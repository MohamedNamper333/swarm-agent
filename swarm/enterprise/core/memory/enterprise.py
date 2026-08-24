"""
Enterprise Memory V2 Integration - Multi-tenant, governed, context-aware memory.
"""

import asyncio
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import logging

from swarm.memory.v2 import (
    MemoryFabric, MemoryLayer, TrustLevel, MemoryMetadata, MemoryEntry,
    MemoryWrite, MemoryQuery, MemoryRead, TrustLevel as TrustLevelEnum,
)

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Models
# =============================================================================

class MemoryAccessLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class MemoryTenantConfig:
    tenant_id: str
    max_entries: int = 100000
    max_entry_size_bytes: int = 1024 * 1024
    retention_days: int = 90
    enable_cross_tenant_search: bool = False
    allowed_layers: List[str] = field(default_factory=lambda: [l.value for l in MemoryLayer])
    pii_detection: bool = True
    encryption_required: bool = True


@dataclass
class MemoryAccessPolicy:
    policy_id: str
    tenant_id: str
    actor_id: str
    actor_type: str
    allowed_layers: List[str]
    allowed_operations: List[str]
    resource_tags: Set[str] = field(default_factory=set)
    conditions: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None


@dataclass
class MemorySearchResult:
    entry: Any
    score: float
    layer: str
    access_allowed: bool = True


@dataclass
class MemoryContext:
    query: str
    tenant_id: str
    results: List[Dict[str, Any]] = field(default_factory=list)
    assembled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    token_estimate: int = 0
    citations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Enterprise Memory Service
# =============================================================================

class EnterpriseMemoryService:
    def __init__(
        self,
        fabric: "MemoryFabric",
        governance_service: Optional[Any] = None,
    ):
        self.fabric = fabric
        self.governance = governance_service
        
        self._tenant_configs: Dict[str, Any] = {}
        self._access_policies: Dict[str, Any] = {}
        self._lock = threading.RLock()
        
        self._pii_patterns = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "phone": r"\+?1?\d{9,15}",
            "ssn": r"\d{3}-\d{2}-\d{4}",
            "credit_card": r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}",
            "api_key": r"(api[_-]?key|secret)[\s:=]+[a-zA-Z0-9_-]{20,}",
        }
        
        self._stats = defaultdict(int)
    
    def register_tenant(self, config: Any) -> None:
        with self._lock:
            self._tenant_configs[config.tenant_id] = config
            logger.info(f"Registered tenant config: {config.tenant_id}")
    
    def get_tenant_config(self, tenant_id: str) -> Any:
        with self._lock:
            return self._tenant_configs.get(tenant_id, type("Config", (), {"allowed_layers": [l.value for l in MemoryLayer], "pii_detection": True, "encryption_required": False})())
    
    def set_access_policy(self, policy: Any) -> None:
        with self._lock:
            self._access_policies[policy.policy_id] = policy
    
    def check_access(
        self,
        tenant_id: str,
        actor_id: str,
        actor_type: str,
        operation: str,
        layer: str,
        resource_tags: Optional[Set[str]] = None,
    ) -> Tuple[bool, Optional[str]]:
        config = self._tenant_configs.get(tenant_id)
        allowed_layers = config.allowed_layers if config else [l.value for l in MemoryLayer]
        if layer not in allowed_layers:
            return False, f"Layer {layer} not allowed for tenant"
        
        for policy in self._access_policies.values():
            if policy.tenant_id != tenant_id:
                continue
            if policy.actor_id != "*" and policy.actor_id != actor_id:
                continue
            if policy.actor_type != "*" and policy.actor_type != actor_type:
                continue
            if layer not in policy.allowed_layers:
                continue
            if operation not in policy.allowed_operations:
                continue
            if policy.resource_tags and resource_tags:
                if not policy.resource_tags.intersection(resource_tags):
                    continue
            if policy.expires_at and policy.expires_at < datetime.now(timezone.utc):
                continue
            return True, None
        
        return False, "No matching access policy"
    
    def write(
        self,
        content: Dict[str, Any],
        layer: str,
        tenant_id: str,
        actor_id: str,
        actor_type: str,
        trust_level: str = "AGENT_GENERATED",
        tags: Optional[Set[str]] = None,
        importance_score: float = 0.5,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        allowed, reason = self.check_access(tenant_id, actor_id, actor_type, "write", layer)
        if not allowed:
            return False, reason, None
        
        config = self._tenant_configs.get(tenant_id)
        if config and config.pii_detection:
            pii_found = self._detect_pii(str(content))
            if pii_found:
                logger.warning(f"PII detected in write: {pii_found}")
                if config.encryption_required:
                    return False, "PII detected but encryption not configured", None
        
        from swarm.memory.v2 import MemoryEntry, MemoryMetadata, MemoryWrite, MemoryLayer, TrustLevel
        
        entry = MemoryEntry(
            metadata=MemoryMetadata(
                layer=MemoryLayer(layer),
                tenant_id=tenant_id,
                actor_id=actor_id,
                trust_level=TrustLevel(trust_level),
                tags=tags or set(),
                importance_score=importance_score,
            ),
            content=content,
        )
        
        write = MemoryWrite(entry=entry)
        
        try:
            import asyncio
            # Use asyncio.run for sync context compatibility
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.fabric._repository.write(MemoryWrite(entry=entry)))
                    memory_id = future.result()
            except RuntimeError:
                # No running loop, safe to use asyncio.run
                memory_id = asyncio.run(self.fabric._repository.write(MemoryWrite(entry=entry)))
            return True, None, memory_id
        except Exception as e:
            logger.error(f"Memory write failed: {e}")
            return False, str(e), None
    
    def read(
        self,
        query: Any,
        actor_id: str,
        actor_type: str,
    ) -> Tuple[List[Any], Optional[str]]:
        tenant_id = query.tenant_id
        
        allowed, reason = self.check_access(tenant_id, actor_id, "agent", "read", query.layer.value if query.layer else "WORKING")
        if not allowed:
            return [], reason
        
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.fabric.read(query))
                    entries = future.result()
            except RuntimeError:
                entries = asyncio.run(self.fabric.read(query))
            return entries, None
        except Exception as e:
            logger.error(f"Memory read failed: {e}")
            return [], str(e)
    
    def search(
        self,
        query: str,
        tenant_id: str,
        actor_id: str,
        actor_type: str,
        top_k: int = 10,
        mode: str = "HYBRID",
        layers: Optional[List[str]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        config = self._tenant_configs.get(tenant_id)
        allowed_layers = config.allowed_layers if config else [l.value for l in MemoryLayer]
        search_layers = layers or allowed_layers
        
        try:
            from swarm.memory.v2 import TrustLevel
            
            search_manager = self.fabric._context_manager
            if not search_manager:
                return [], "Search not available"
            
            all_results = []
            for layer_str in search_layers:
                if layer_str not in allowed_layers:
                    continue
                
                allowed, _ = self.check_access(tenant_id, "agent", "agent", "read", layer_str)
                if not allowed:
                    continue
                
                try:
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run,
                                self.fabric.search(
                                    query_text=query,
                                    actor="agent",
                                    actor_trust=TrustLevel.VERIFIED,
                                    actor_tenant=tenant_id,
                                    layer=MemoryLayer(layer_str),
                                    top_k=top_k,
                                )
                            )
                            results = future.result()
                    except RuntimeError:
                        results = asyncio.run(self.fabric.search(
                            query_text=query,
                            actor="agent",
                            actor_trust=TrustLevel.VERIFIED,
                            actor_tenant=tenant_id,
                            layer=MemoryLayer(layer_str),
                            top_k=top_k,
                        ))
                    
                    config = self._tenant_configs.get(tenant_id)
                    for entry, score in results:
                        allowed, _ = self.check_access(tenant_id, "agent", "agent", "read", layer_str)
                        if not allowed:
                            continue
                        
                        content = entry.content
                        if config and config.pii_detection:
                            content = self._redact_pii(content)
                        
                        all_results.append({
                            "entry": entry,
                            "score": score,
                            "layer": layer_str,
                        })
                except Exception as e:
                    logger.warning(f"Search failed for layer {layer_str}: {e}")
            
            all_results.sort(key=lambda r: r["score"], reverse=True)
            return all_results[:10], None
            
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return [], str(e)
    
    def assemble_context(
        self,
        query: str,
        tenant_id: str,
        actor_id: str,
        actor_type: str,
        top_k: int = 10,
        max_tokens: int = 4000,
    ) -> Tuple[Any, Optional[str]]:
        results, error = self.search(query, tenant_id, actor_id, "agent", top_k=top_k)
        if error:
            return None, error
        
        class Context:
            def __init__(self):
                self.query = query
                self.tenant_id = tenant_id
                self.results = []
                self.token_estimate = 0
                self.citations = []
        
        context = type("Context", (), {
            "query": query,
            "tenant_id": tenant_id,
            "results": [],
            "token_estimate": 0,
            "citations": [],
        })()
        
        total_tokens = 0
        for i, result in enumerate(results):
            entry = result["entry"]
            score = result["score"]
            layer = result["layer"]
            
            content_str = str(entry.content)
            est_tokens = len(content_str) // 4
            
            if total_tokens + est_tokens > 4000:
                break
            
            total_tokens += est_tokens
            context.results.append({"entry": entry, "score": score, "layer": layer})
            
            context.citations.append({
                "index": len(context.citations),
                "source": layer,
                "memory_id": entry.metadata.memory_id,
                "score": score,
                "preview": str(entry.content)[:200],
            })
        
        context.token_estimate = total_tokens
        return context, None
    
    def record_episode(
        self,
        workflow_id: str,
        workflow_type: str,
        status: str,
        steps: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        tenant_id: str,
        actor_id: str = "system",
    ) -> bool:
        success, _, _ = self.write(
            content={
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "status": status,
                "steps": steps,
                "metrics": metrics,
            },
            layer="EPISODIC",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type="system",
            trust_level="SYSTEM_DERIVED",
            tags={"episode", workflow_type},
            importance_score=0.7,
        )
        return success
    
    def _detect_pii(self, text: str) -> List[str]:
        found = []
        for pii_type, pattern in self._pii_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                found.append(f"{pii_type}: {len(matches)} matches")
        return found
    
    def _redact_pii(self, content: Any) -> Any:
        if isinstance(content, str):
            text = content
            for pii_type, pattern in self._pii_patterns.items():
                text = re.sub(pattern, f"[REDACTED:{pii_type.upper()}]", text)
            return text
        elif isinstance(content, dict):
            return {k: self._redact_pii(v) for k, v in content.items()}
        elif isinstance(content, list):
            return [self._redact_pii(item) for item in content]
        return content
    
    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)
    
    def health_check(self) -> bool:
        return True
    
    def __init__(
        self,
        fabric: "MemoryFabric",
        governance_service: Optional[Any] = None,
    ):
        self.fabric = fabric
        self.governance = governance_service
        
        self._tenant_configs: Dict[str, Any] = {}
        self._access_policies: Dict[str, Any] = {}
        self._lock = threading.RLock()
        
        self._pii_patterns = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "phone": r"\+?1?\d{9,15}",
            "ssn": r"\d{3}-\d{2}-\d{4}",
            "credit_card": r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}",
            "api_key": r"(api[_-]?key|secret)[\s:=]+[a-zA-Z0-9_-]{20,}",
        }
        
        self._stats = defaultdict(int)
    
    def register_tenant(self, config: Any) -> None:
        with self._lock:
            self._tenant_configs[config.tenant_id] = config
            logger.info(f"Registered tenant config: {config.tenant_id}")
    
    def get_tenant_config(self, tenant_id: str) -> Any:
        with self._lock:
            return self._tenant_configs.get(tenant_id)
    
    def set_access_policy(self, policy: Any) -> None:
        with self._lock:
            self._access_policies[policy.policy_id] = policy
    
    def check_access(
        self,
        tenant_id: str,
        actor_id: str,
        actor_type: str,
        operation: str,
        layer: str,
        resource_tags: Optional[Set[str]] = None,
    ) -> Tuple[bool, Optional[str]]:
        config = self._tenant_configs.get(tenant_id)
        allowed_layers = config.allowed_layers if config else [l.value for l in MemoryLayer]
        if layer not in allowed_layers:
            return False, f"Layer {layer} not allowed for tenant"
        
        for policy in self._access_policies.values():
            if policy.tenant_id != tenant_id:
                continue
            if policy.actor_id != "*" and policy.actor_id != actor_id:
                continue
            if policy.actor_type != "*" and policy.actor_type != actor_type:
                continue
            if layer not in policy.allowed_layers:
                continue
            if operation not in policy.allowed_operations:
                continue
            if policy.resource_tags and resource_tags:
                if not policy.resource_tags.intersection(resource_tags):
                    continue
            if policy.expires_at and policy.expires_at < datetime.now(timezone.utc):
                continue
            return True, None
        
        return False, "No matching access policy"
    
    def write(
        self,
        content: Dict[str, Any],
        layer: str,
        tenant_id: str,
        actor_id: str,
        actor_type: str,
        trust_level: str = "AGENT_GENERATED",
        tags: Optional[Set[str]] = None,
        importance_score: float = 0.5,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        allowed, reason = self.check_access(tenant_id, actor_id, actor_type, "write", layer)
        if not allowed:
            return False, reason, None
        
        config = self._tenant_configs.get(tenant_id)
        if config and config.pii_detection:
            pii_found = self._detect_pii(str(content))
            if pii_found:
                logger.warning(f"PII detected in write: {pii_found}")
                if config.encryption_required:
                    return False, "PII detected but encryption not configured", None
        
        from swarm.memory.v2 import MemoryEntry, MemoryMetadata, MemoryWrite, MemoryLayer, TrustLevel
        
        entry = MemoryEntry(
            metadata=MemoryMetadata(
                layer=MemoryLayer(layer),
                tenant_id=tenant_id,
                actor_id=actor_id,
                trust_level=TrustLevel(trust_level),
                tags=tags or set(),
                importance_score=importance_score,
            ),
            content=content,
        )
        
        try:
            import asyncio
            # Use asyncio.run for sync context compatibility
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.fabric._repository.write(MemoryWrite(entry=entry)))
                    memory_id = future.result()
            except RuntimeError:
                # No running loop, safe to use asyncio.run
                memory_id = asyncio.run(self.fabric._repository.write(MemoryWrite(entry=entry)))
            return True, None, memory_id
        except Exception as e:
            logger.error(f"Memory write failed: {e}")
            return False, str(e), None
    
    def _detect_pii(self, text: str) -> List[str]:
        found = []
        for pii_type, pattern in self._pii_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                found.append(f"{pii_type}: {len(matches)} matches")
        return found
    
    def _redact_pii(self, content: Any) -> Any:
        if isinstance(content, str):
            text = content
            for pii_type, pattern in self._pii_patterns.items():
                text = re.sub(pattern, f"[REDACTED:{pii_type.upper()}]", text)
            return text
        elif isinstance(content, dict):
            return {k: self._redact_pii(v) for k, v in content.items()}
        elif isinstance(content, list):
            return [self._redact_pii(item) for item in content]
        return content


# =============================================================================
# Models (for external use)
# =============================================================================

class MemoryAccessLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class MemoryTenantConfig:
    tenant_id: str
    max_entries: int = 100000
    max_entry_size_bytes: int = 1024 * 1024
    retention_days: int = 90
    enable_cross_tenant_search: bool = False
    allowed_layers: List[str] = field(default_factory=lambda: [l.value for l in MemoryLayer])
    pii_detection: bool = True
    encryption_required: bool = True


@dataclass
class MemoryAccessPolicy:
    policy_id: str
    tenant_id: str
    actor_id: str
    actor_type: str
    allowed_layers: List[str]
    allowed_operations: List[str]
    resource_tags: Set[str] = field(default_factory=set)
    conditions: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None


@dataclass
class MemorySearchResult:
    entry: Any
    score: float
    layer: str
    access_allowed: bool = True


@dataclass
class MemoryContext:
    query: str
    tenant_id: str
    results: List[Dict[str, Any]] = field(default_factory=list)
    assembled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    token_estimate: int = 0
    citations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Memory Assembler
# =============================================================================

class MemoryAssembler:
    def __init__(self, memory_service: "EnterpriseMemoryService"):
        self.memory_service = memory_service
    
    def assemble_for_agent(
        self,
        query: str,
        tenant_id: str,
        agent_id: str,
        max_tokens: int = 4000,
    ) -> Tuple[Optional[Any], Optional[str]]:
        return self.memory_service.assemble_context(
            query=query,
            tenant_id=tenant_id,
            actor_id=agent_id,
            actor_type="agent",
            top_k=10,
            max_tokens=max_tokens,
        )


# =============================================================================
# Factory
# =============================================================================

def create_enterprise_memory_service(
    fabric: "MemoryFabric",
    governance_service: Optional[Any] = None,
) -> "EnterpriseMemoryService":
    return EnterpriseMemoryService(fabric, governance_service)
