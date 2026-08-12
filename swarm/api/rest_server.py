"""
REST Server Module - FastAPI-based REST API for Swarm
Provides endpoints for tasks, agents, models, vault, and system health.
"""
import asyncio
import logging
import os
import tempfile
import threading
import time
import httpx
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from swarm.resilience.task_queue import TaskQueue
from swarm.core.agent_state_machine import AgentState as ASState
from swarm.api.auth import get_auth_manager, require_scopes

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


# Pydantic models for API
class TaskCreate(BaseModel):
    name: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    max_attempts: int = 3
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    id: str
    name: str
    payload: Dict[str, Any]
    priority: TaskPriority
    status: TaskStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    attempts: int
    max_attempts: int
    result: Optional[Dict] = None
    error: Optional[str] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class ModelHealthResponse(BaseModel):
    model_id: str
    healthy: bool
    latency_ms: float
    last_check: str
    consecutive_failures: int


class AgentStateResponse(BaseModel):
    agent_id: str
    state: str
    current_task: Optional[str] = None
    time_in_state_seconds: float
    last_active: Optional[str] = None


class SystemHealthResponse(BaseModel):
    status: str
    timestamp: str
    components: Dict[str, Any]


# Request/Response models
class ConstitutionalCheckRequest(BaseModel):
    artifact_id: str
    artifact_content: str
    agent_id: str = "api"


class ConstitutionalCheckResponse(BaseModel):
    artifact_id: str
    status: str
    violations: List[Dict]
    requires_human_review: bool


class SkillDiscoveryRequest(BaseModel):
    task_description: str
    top_k: int = 5
    required_category: Optional[str] = None


class SkillMatchResponse(BaseModel):
    skill_id: str
    skill_name: str
    match_strength: str
    match_score: float
    matched_keywords: List[str]
    category: str


# Global references (set by initialize_app)
_task_queue = None
_model_registry = None
_agent_state = None
_constitutional_guard = None
_skill_discovery = None


class _AgentRegistry:
    """In-memory agent registry — real, no demo data fallback.

    Tracks agent state transitions so the dashboard sees live workers,
    not hard-coded demo strings.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._agents: Dict[str, Dict[str, Any]] = {}

    def register(self, agent_id: str, state: ASState):
        with self._lock:
            self._agents[agent_id] = {
                "state": state,
                "current_task": None,
                "entered_state_at": time.time(),
                "last_active": datetime.now(timezone.utc).isoformat(),
            }

    def transition(self, agent_id: str, state: ASState, current_task: Optional[str] = None):
        with self._lock:
            if agent_id not in self._agents:
                self.register(agent_id, state)
                return
            self._agents[agent_id]["state"] = state
            self._agents[agent_id]["current_task"] = current_task
            self._agents[agent_id]["entered_state_at"] = time.time()
            self._agents[agent_id]["last_active"] = datetime.now(timezone.utc).isoformat()

    def list_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            now = time.time()
            out = []
            for agent_id, rec in self._agents.items():
                out.append({
                    "agent_id": agent_id,
                    "state": rec["state"].value,
                    "current_task": rec["current_task"],
                    "time_in_state_seconds": round(now - rec["entered_state_at"], 1),
                    "last_active": rec["last_active"],
                })
            return out

    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._agents.get(agent_id)


def set_dependencies(
    task_queue,
    model_registry,
    agent_state,
    constitutional_guard,
    skill_discovery
):
    global _task_queue, _model_registry, _agent_state, _constitutional_guard, _skill_discovery
    _task_queue = task_queue
    _model_registry = model_registry
    _agent_state = agent_state
    _constitutional_guard = constitutional_guard
    _skill_discovery = skill_discovery


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager — builds real TaskQueue + AgentRegistry."""
    global _task_queue, _agent_state
    logger.info("Starting Swarm REST API server...")

    storage = Path(os.environ.get("SWARM_QUEUE_PATH",
                                  tempfile.mkdtemp(prefix="swarm_queue_")))
    storage.mkdir(parents=True, exist_ok=True)
    _task_queue = TaskQueue(storage_path=storage)
    logger.info(f"TaskQueue ready at {storage} (loaded {_task_queue.size()} tasks)")

    _agent_state = _AgentRegistry()
    _agent_state.register("orchestrator-01", ASState.IDLE)
    _agent_state.register("coder-01", ASState.IDLE)
    _agent_state.register("reviewer-01", ASState.IDLE)
    _agent_state.register("researcher-01", ASState.IDLE)
    logger.info("AgentRegistry ready (4 agents registered)")

    try:
        yield
    finally:
        logger.info("Shutting down Swarm REST API server...")


app = FastAPI(
    title="Swarm API",
    description="REST API for the Swarm Agent System",
    version="3.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== Vault Proxy ==========

@app.get("/vault/search")
async def vault_search(q: str = "", limit: int = 20):
    """Proxy search to the Obsidian Vault REST server."""
    vault_url = os.environ.get("VAULT_SERVER_URL", "http://127.0.0.1:27123")
    vault_key = os.environ.get("VAULT_API_KEY", "swarm-evolution-2025")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{vault_url}/search/simple/",
                params={"query": q, "contextLength": 100},
                headers={"Authorization": f"Bearer {vault_key}"},
            )
            r.raise_for_status()
            data = r.json()
            hits = data.get("hits", [])
            return {"results": hits[:limit], "total": len(hits)}
    except Exception as e:
        logger.warning(f"Vault search failed: {e}")
        return {"results": [], "total": 0, "error": str(e)}


# ========== Health & System ==========

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/health/system", response_model=SystemHealthResponse)
async def system_health():
    """Detailed system health"""
    return SystemHealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        components={
            "api": "healthy",
            "task_queue": "healthy" if _task_queue else "unavailable",
            "model_registry": "healthy" if _model_registry else "unavailable",
            "constitutional_guard": "healthy" if _constitutional_guard else "unavailable"
        }
    )


# ========== Tasks ==========

def _task_item_to_response(item) -> TaskResponse:
    """Convert a TaskQueue QueueItem to the REST TaskResponse model."""
    tags = []
    if item.metadata and isinstance(item.metadata, dict):
        tags = item.metadata.get("tags", [])

    # Map queue status -> API status (pending -> queued, dead_letter -> failed)
    api_status_map = {
        "pending": TaskStatus.QUEUED,
        "running": TaskStatus.RUNNING,
        "completed": TaskStatus.COMPLETED,
        "failed": TaskStatus.FAILED,
        "cancelled": TaskStatus.CANCELLED,
        "dead_letter": TaskStatus.FAILED,
    }
    api_status = api_status_map.get(item.status, TaskStatus.QUEUED)

    # Convert timestamps to ISO strings
    def iso(ts):
        if ts is None:
            return None
        return datetime.fromtimestamp(ts, timezone.utc).isoformat()

    return TaskResponse(
        id=item.id,
        name=item.task_type,
        payload=item.payload,
        priority=TaskPriority(item.priority),
        status=api_status,
        created_at=iso(item.created_at),
        started_at=iso(item.started_at),
        completed_at=iso(item.completed_at),
        attempts=item.attempts,
        max_attempts=item.max_attempts,
        result=None,
        error=item.last_error,
        tags=tags,
        metadata=item.metadata or {},
    )


@app.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(task: TaskCreate, background_tasks: BackgroundTasks):
    """Create and enqueue a new task — real TaskQueue."""
    if not _task_queue:
        raise HTTPException(503, "Task queue not available")

    item = _task_queue.enqueue(
        task_type=task.name,
        payload=task.payload,
        priority=task.priority.value,
        max_attempts=task.max_attempts,
        metadata={"tags": task.tags, **task.metadata},
    )

    return _task_item_to_response(item)


@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    limit: int = 50
):
    """List tasks with optional filters — real TaskQueue, no demo data."""
    if not _task_queue:
        raise HTTPException(503, "Task queue not initialized")

    all_tasks: List[Any] = []
    if priority:
        all_tasks.extend(_task_queue.list(priority=priority.value))
    else:
        all_tasks.extend(_task_queue.list())

    if status:
        wanted = {status.value}
        if status.value == "queued":
            wanted = {"pending"}
        elif status.value == "failed":
            wanted = {"failed", "dead_letter"}
        all_tasks = [t for t in all_tasks if t.status in wanted]

    all_tasks = all_tasks[:limit]

    return [_task_item_to_response(t) for t in all_tasks]


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Get task by ID"""
    if not _task_queue:
        raise HTTPException(503, "Task queue not available")

    task = _task_queue.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    return _task_item_to_response(task)


@app.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a task"""
    if not _task_queue:
        raise HTTPException(503, "Task queue not available")

    success = _task_queue.cancel(task_id)
    if not success:
        raise HTTPException(404, "Task not found or not cancellable")

    return {"message": "Task cancelled", "task_id": task_id}


@app.post("/tasks/{task_id}/retry")
async def retry_task(task_id: str):
    """Retry a failed task"""
    if not _task_queue:
        raise HTTPException(503, "Task queue not available")
    
    # For retry, we need to fail it with retry=True
    # This is a simplified approach
    task = _task_queue.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    if task.status not in ["failed", "dead_letter"]:
        raise HTTPException(400, "Can only retry failed tasks")

    # Re-enqueue by canceling and re-enqueuing
    _task_queue.cancel(task_id)
    new_item = _task_queue.enqueue(
        task_type=task.task_type,
        payload=task.payload,
        priority=task.priority,
        max_attempts=task.max_attempts,
        metadata=task.metadata,
    )

    return {"message": "Task re-enqueued", "new_task_id": new_item.id}


# ========== Models ==========

@app.get("/models", response_model=List[ModelHealthResponse])
async def list_models():
    """List all models with health status"""
    if not _model_registry:
        raise HTTPException(503, "Model registry not available")
    
    # This would need integration with actual ModelRegistry
    return []


@app.get("/models/{model_id}/health", response_model=ModelHealthResponse)
async def model_health(model_id: str):
    """Get model health"""
    if not _model_registry:
        raise HTTPException(503, "Model registry not available")
    
    # Placeholder
    raise HTTPException(404, "Model not found")


# ========== Agents ==========

@app.get("/agents", response_model=List[AgentStateResponse])
async def list_agents():
    """List all agents and their states — real AgentRegistry, no demo data."""
    if not _agent_state:
        raise HTTPException(503, "Agent registry not initialized")

    return [
        AgentStateResponse(
            agent_id=rec["agent_id"],
            state=rec["state"],
            current_task=rec["current_task"],
            time_in_state_seconds=rec["time_in_state_seconds"],
            last_active=rec["last_active"],
        )
        for rec in _agent_state.list_all()
    ]


@app.get("/agents/{agent_id}/state", response_model=AgentStateResponse)
async def agent_state(agent_id: str):
    """Get agent state"""
    if not _agent_state:
        raise HTTPException(503, "Agent state not available")
    
    raise HTTPException(404, "Agent not found")


# ========== Constitutional Guard ==========

@app.post("/constitutional/check", response_model=ConstitutionalCheckResponse)
async def constitutional_check(request: ConstitutionalCheckRequest):
    """Check artifact against constitutional principles"""
    if not _constitutional_guard:
        raise HTTPException(503, "Constitutional guard not available")
    
    result = _constitutional_guard.check_artifact(
        artifact_id=request.artifact_id,
        artifact_content=request.artifact_content,
        agent_id=request.agent_id
    )
    
    return ConstitutionalCheckResponse(
        artifact_id=result.artifact_id,
        status=result.status.value,
        violations=[
            {
                "principle": v.principle.value,
                "severity": v.severity.value,
                "evidence": v.evidence,
                "recommendation": v.recommendation
            }
            for v in result.violations
        ],
        requires_human_review=result.requires_human_review
    )


# ========== Skill Discovery ==========

@app.post("/skills/discover", response_model=List[SkillMatchResponse])
async def discover_skills(request: SkillDiscoveryRequest):
    """Discover skills for a task"""
    if not _skill_discovery:
        raise HTTPException(503, "Skill discovery not available")
    
    category = None
    if request.required_category:
        from swarm.intelligence.skill_discovery import SkillCategory
        category = SkillCategory(request.required_category)
    
    matches = _skill_discovery.discover_skills_for_task(
        task_description=request.task_description,
        top_k=request.top_k,
        required_category=category
    )
    
    return [
        SkillMatchResponse(
            skill_id=m.skill_id,
            skill_name=m.skill_name,
            match_strength=m.match_strength.value,
            match_score=m.match_score,
            matched_keywords=m.matched_keywords,
            category=m.category.value
        )
        for m in matches
    ]


@app.get("/skills")
async def list_skills(category: Optional[str] = None):
    """List available skills"""
    if not _skill_discovery:
        raise HTTPException(503, "Skill discovery not available")
    
    if category:
        from swarm.intelligence.skill_discovery import SkillCategory
        skills = _skill_discovery.list_skills_by_category(SkillCategory(category))
    else:
        skills = list(_skill_discovery.skill_index.values())
    
    return [
        {
            "skill_id": s.skill_id,
            "name": s.name,
            "category": s.category.value,
            "description": s.description,
            "keywords": s.keywords[:10],
            "usage_count": s.usage_count,
            "avg_success_rate": s.avg_success_rate
        }
        for s in skills
    ]


# ========== Queue Stats ==========

@app.get("/queue/stats")
async def queue_stats():
    """Get queue statistics"""
    if not _task_queue:
        raise HTTPException(503, "Task queue not available")

    return {
        "size": _task_queue.size(),
        "status": _task_queue.get_status().value,
        "breakdown": _task_queue.status_breakdown(),
    }


# ========== Metrics ==========

@app.get("/metrics")
async def metrics_prometheus():
    """Prometheus metrics endpoint"""
    from swarm.observability.metrics_server import get_metrics_server
    server = get_metrics_server()
    return server.export_prometheus()


@app.get("/metrics/json")
async def metrics_json():
    """JSON metrics endpoint"""
    from swarm.observability.metrics_server import get_metrics_server
    server = get_metrics_server()
    snapshot = server.get_snapshot()
    return {
        "counters": snapshot.counters,
        "gauges": snapshot.gauges,
        "histograms": {
            k: {"count": v["count"], "sum": v["sum"]}
            for k, v in snapshot.histograms.items()
        }
    }


# ========== Enterprise: VETO & Budget ==========

def _validate_agent_id(agent_id: str) -> str:
    """Validate agent_id to prevent path traversal and injection.

    agent_id must be alphanumeric + hyphens/underscores, max 128 chars.
    """
    if not agent_id or len(agent_id) > 128:
        raise HTTPException(400, "agent_id must be 1-128 chars")
    if not all(c.isalnum() or c in "-_." for c in agent_id):
        raise HTTPException(
            400, "agent_id may only contain letters, digits, '-', '_', '.'"
        )
    return agent_id


class VetoRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=128,
                          pattern=r"^[A-Za-z0-9._-]+$")
    vetoed_by: str = Field(..., min_length=1, max_length=128,
                           pattern=r"^[A-Za-z0-9._@-]+$")
    category: str = Field(..., min_length=1, max_length=64,
                          pattern=r"^[A-Za-z0-9_-]+$")
    reason: str = Field(..., min_length=1, max_length=500)
    context: Optional[Dict[str, Any]] = None


class VetoResponse(BaseModel):
    agent_id: str
    vetoed: bool
    veto_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class VetoOverrideRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=128,
                          pattern=r"^[A-Za-z0-9._-]+$")
    override_by: str = Field(..., min_length=1, max_length=128,
                             pattern=r"^[A-Za-z0-9._@-]+$")
    reason: str = Field(..., min_length=1, max_length=500)


class VetoOverrideResponse(BaseModel):
    agent_id: str
    overridden: bool
    error: Optional[str] = None


# Registry of enterprise state machines (VETO-capable)
_enterprise_state_machines: Dict[str, Any] = {}


def register_enterprise_sm(agent_id: str, sm) -> None:
    """Register an AgentStateMachine for VETO API access."""
    _enterprise_state_machines[agent_id] = sm


@app.post("/veto", response_model=VetoResponse)
async def apply_veto(
    request: VetoRequest,
    user: Dict[str, Any] = Depends(require_scopes("agents:write")),
):
    """Apply absolute VETO to an agent (ethics/safety override).

    Requires agents:write scope. ADMIN scope implicitly grants this
    via the auth manager's scope hierarchy.
    """
    from swarm.core.agent_state_machine import AgentStateMachine

    _validate_agent_id(request.agent_id)
    sm = _enterprise_state_machines.get(request.agent_id)
    if not sm:
        # إنشاء واحدة جديدة للاختبار
        sm = AgentStateMachine(request.agent_id)
        sm.transition(sm.state.__class__.ASSIGNED, "auto-created for VETO")
        _enterprise_state_machines[request.agent_id] = sm

    success = sm.veto(
        vetoed_by=request.vetoed_by,
        category=request.category,
        reason=request.reason,
    )
    if not success:
        return VetoResponse(
            agent_id=request.agent_id,
            vetoed=False,
            error="VETO transition failed",
        )
    return VetoResponse(
        agent_id=request.agent_id,
        vetoed=True,
        veto_info=sm.veto_info,
    )


@app.post("/veto/override", response_model=VetoOverrideResponse)
async def override_veto(
    request: VetoOverrideRequest,
    user: Dict[str, Any] = Depends(require_scopes("admin")),
):
    """Manually override VETO and return agent to IDLE.

    Requires ADMIN scope only — VETO override is a privileged operation.
    """
    _validate_agent_id(request.agent_id)
    sm = _enterprise_state_machines.get(request.agent_id)
    if not sm:
        return VetoOverrideResponse(
            agent_id=request.agent_id,
            overridden=False,
            error="Agent not found or not VETOED",
        )
    # Record who actually authorized this via the auth header.
    authorized_by = user.get("sub", "unknown")
    audit_reason = (
        f"[auth={authorized_by}] override_by={request.override_by}: "
        f"{request.reason}"
    )
    success = sm.override_veto(
        override_by=authorized_by,
        reason=audit_reason,
    )
    return VetoOverrideResponse(
        agent_id=request.agent_id,
        overridden=success,
        error=None if success else "Override failed",
    )


@app.get("/veto/{agent_id}")
async def get_veto_status(
    agent_id: str,
    user: Dict[str, Any] = Depends(require_scopes("agents:read")),
):
    """Get VETO status of an agent.

    Requires agents:read scope. ADMIN scope implicitly grants this.
    """
    sm = _enterprise_state_machines.get(agent_id)
    if not sm:
        raise HTTPException(404, f"Agent {agent_id} not registered")
    return {
        "agent_id": agent_id,
        "is_vetoed": sm.state.name == "VETOED",
        "veto_info": sm.veto_info,
        "current_state": sm.state.name,
        "valid_transitions": sm.get_valid_transitions(),
    }


@app.get("/veto")
async def list_vetoed_agents(
    user: Dict[str, Any] = Depends(require_scopes("agents:read")),
):
    """List all currently VETOED agents.

    Requires agents:read scope. ADMIN scope implicitly grants this.
    """
    vetoed = []
    for agent_id, sm in _enterprise_state_machines.items():
        if sm.state.name == "VETOED":
            vetoed.append({
                "agent_id": agent_id,
                "veto_info": sm.veto_info,
                "vetoed_at": sm.state_entry_time.isoformat(),
                "time_in_state_seconds": sm.time_in_state(),
            })
    return {"vetoed_agents": vetoed, "count": len(vetoed)}


# ========== Budget Tracking ==========

class BudgetRequest(BaseModel):
    action: str  # "check" | "record" | "report"
    model_id: Optional[str] = None
    tokens_used: Optional[int] = None
    daily_limit: Optional[int] = None


class BudgetResponse(BaseModel):
    action: str
    model_id: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    allowed: Optional[bool] = None
    remaining: Optional[int] = None


@app.post("/budget")
async def budget_action(request: BudgetRequest):
    """Budget tracking: check, record, report."""
    try:
        from swarm.resilience.rate_limiter_v2 import get_rate_limiter
        limiter = get_rate_limiter()

        if request.action == "check":
            allowed, current, limit = limiter.check_limit(request.model_id)
            return BudgetResponse(
                action="check",
                model_id=request.model_id,
                allowed=allowed,
                remaining=limit - current,
                usage={"current": current, "limit": limit},
            )
        elif request.action == "record":
            allowed = limiter.record_usage(request.model_id, request.tokens_used or 1)
            return BudgetResponse(
                action="record",
                model_id=request.model_id,
                allowed=allowed,
            )
        elif request.action == "report":
            report = limiter.get_report()
            return {"action": "report", "report": report}
        else:
            raise HTTPException(400, f"Unknown action: {request.action}")
    except Exception as e:
        raise HTTPException(500, str(e))


# ========== Enterprise: SwarmMaster + Department Endpoints ==========
#
# Phase C: REST API coverage for all 10 departments
# Provides direct HTTP access to:
# - /swarm/process (Master endpoint)
# - /board/deliberate
# - /csuite/meeting, /csuite/budget
# - /code/pipeline, /code/review
# - /design/brand-kit, /design/image
# - /video/promo
# - /research/full
# - /data/analyze
# - /language/translate
# - /knowledge/query
# - /safety/check
# - /swarm/status, /swarm/agents (info)

# Global SwarmMaster instance (lazy init)
_swarm_master = None


def get_swarm_master():
    """يرجع SwarmMaster singleton."""
    global _swarm_master
    if _swarm_master is None:
        from swarm.enterprise.swarm_master import SwarmMaster
        _swarm_master = SwarmMaster()
    return _swarm_master


# ========== Request Models ==========

class SwarmProcessRequest(BaseModel):
    """طلب لمعالجته عبر SwarmMaster."""
    question: str
    type: str = "general"
    estimated_cost: float = 0.0
    context: Dict[str, Any] = Field(default_factory=dict)
    bypass_safety: bool = False


class BoardDeliberateRequest(BaseModel):
    """طلب لمناقشة المجلس."""
    question: str
    context: Dict[str, Any] = Field(default_factory=dict)


class CSuiteMeetingRequest(BaseModel):
    """طلب لاجتماع C-Suite."""
    proposal: Dict[str, Any]


class CodeReviewRequest(BaseModel):
    """طلب لمراجعة كود."""
    code: str
    language: str = "python"


class DesignBrandKitRequest(BaseModel):
    """طلب لـ brand kit."""
    brand_name: str


class DesignImageRequest(BaseModel):
    """طلب لتوليد صورة."""
    prompt: str
    width: int = 1024
    height: int = 1024


class VideoPromoRequest(BaseModel):
    """طلب لفيديو ترويجي."""
    title: str
    description: str
    target_audience: str = ""


class ResearchRequest(BaseModel):
    """طلب بحثي."""
    query: str


class DataQuestionRequest(BaseModel):
    """طلب لتحليل بيانات."""
    question: str


class TranslationRequest(BaseModel):
    """طلب ترجمة."""
    text: str
    source_lang: str = "en"
    target_lang: str = "ar"


class KnowledgeQueryRequest(BaseModel):
    """طلب استعلام قاعدة معرفة."""
    question: str


class SafetyCheckRequest(BaseModel):
    """طلب فحص محتوى."""
    text: str
    use_llm: bool = False


# ========== Endpoints ==========

@app.post("/swarm/process")
async def swarm_process(request: SwarmProcessRequest):
    """Master endpoint: معالجة طلب عبر كل الـ tiers (Safety → Board → C-Suite → Dept)."""
    from swarm.enterprise.swarm_master import SwarmRequest
    master = get_swarm_master()
    req = SwarmRequest(
        question=request.question,
        type=request.type,
        estimated_cost=request.estimated_cost,
        context=request.context,
        bypass_safety=request.bypass_safety,
    )
    result = master.process(req)
    return {
        "request_id": result.request_id,
        "verdict": result.verdict,
        "final_decision": result.final_decision,
        "vetoed_by": result.vetoed_by,
        "veto_reason": result.veto_reason,
        "executed_by": result.executed_by,
        "stages": result.stages,
        "output": str(result.output)[:500] if result.output else None,
        "metadata": result.metadata,
    }


@app.get("/swarm/status")
async def swarm_status():
    """حالة الـ SwarmMaster."""
    master = get_swarm_master()
    return master.get_status()


@app.get("/swarm/agents")
async def swarm_agents():
    """قائمة بكل الـ agents حسب القسم."""
    master = get_swarm_master()
    return master.list_agents()


@app.post("/board/deliberate")
async def board_deliberate(request: BoardDeliberateRequest):
    """يدعو المجلس لمناقشة اقتراح."""
    master = get_swarm_master()
    result = master.board.deliberate(request.question, context=str(request.context))
    return {
        "verdict": result.final_decision,
        "vetoed_by": result.vetoed_by,
        "veto_reason": result.veto_reason,
        "votes": result.votes,
    }


@app.post("/csuite/meeting")
async def csuite_meeting(request: CSuiteMeetingRequest):
    """يدعو C-Suite لاجتماع تنفيذي."""
    master = get_swarm_master()
    return master.csuite.executive_meeting(request.proposal)


@app.get("/csuite/budget")
async def csuite_budget():
    """حالة ميزانية CFO."""
    master = get_swarm_master()
    return master.csuite.cfo.get_status()


@app.post("/code/review")
async def code_review(request: CodeReviewRequest):
    """مراجعة كود عبر CodeReviewer."""
    master = get_swarm_master()
    from swarm.enterprise.code import Severity
    report = master.depts["code"].reviewer.full_review(request.code, request.language)
    return {
        "approved": report.approved,
        "score": report.total_score,
        "findings_count": len(report.findings),
        "critical": sum(1 for f in report.findings if f.severity == Severity.CRITICAL),
        "high": sum(1 for f in report.findings if f.severity == Severity.HIGH),
        "findings": [
            {
                "severity": f.severity.value,
                "line": f.line,
                "description": f.description,
                "cwe_id": f.cwe_id,
            }
            for f in report.findings[:10]
        ],
    }


@app.post("/design/brand-kit")
async def design_brand_kit(request: DesignBrandKitRequest):
    """يولّد brand kit كامل."""
    master = get_swarm_master()
    return master.depts["design"].generate_complete_brand_kit(request.brand_name)


@app.post("/design/image")
async def design_image(request: DesignImageRequest):
    """يولّد صورة."""
    master = get_swarm_master()
    asset = master.depts["design"].image_gen_1.generate(
        request.prompt, request.width, request.height
    )
    return {
        "type": asset.asset_type.value,
        "format": asset.format.value,
        "author": asset.author,
        "metadata": asset.metadata,
    }


@app.post("/video/promo")
async def video_promo(request: VideoPromoRequest):
    """ينشئ فيديو ترويجي."""
    master = get_swarm_master()
    from swarm.enterprise.video import VideoDuration, VideoFormat
    brief = {"title": request.title, "description": request.description, "target_audience": request.target_audience}
    result = master.depts["video"].create_promo_video(brief)
    return result


@app.post("/research/full")
async def research_full(request: ResearchRequest):
    """بحث شامل: تخطيط → بحث → fact check."""
    master = get_swarm_master()
    return master.depts["research"].full_research(request.query)


@app.post("/data/analyze")
async def data_analyze(request: DataQuestionRequest):
    """تحليل سؤال بيانات."""
    master = get_swarm_master()
    return master.depts["data"].analyze_question(request.question)


@app.post("/language/translate")
async def language_translate(request: TranslationRequest):
    """ترجمة نص."""
    master = get_swarm_master()
    result = master.depts["language"].translator.translate(
        request.text, request.source_lang, request.target_lang
    )
    return {
        "translated_text": result.translated_text,
        "source_lang": result.source_lang,
        "target_lang": result.target_lang,
        "confidence": result.confidence,
        "model": result.model_used,
    }


@app.post("/knowledge/query")
async def knowledge_query(request: KnowledgeQueryRequest):
    """استعلام قاعدة المعرفة."""
    master = get_swarm_master()
    result = master.depts["knowledge"].query(request.question, top_k=3, rerank=True)
    return {
        "query": result.query,
        "documents": [
            {"score": d.score, "content": d.content[:200]}
            for d in result.documents
        ],
        "reranked": result.reranked,
        "total_score": result.total_score,
    }


@app.post("/safety/check")
async def safety_check(request: SafetyCheckRequest):
    """فحص محتوى عبر Safety Dept."""
    master = get_swarm_master()
    report = master.safety_dept.full_check(request.text, use_llm=request.use_llm)
    return {
        "verdict": report.verdict.value,
        "flags": report.flags,
        "explanation": report.explanation,
        "analyst_votes": {k: v.value for k, v in report.analyst_votes.items()},
    }


# Run with: uvicorn swarm.api.rest_server:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)