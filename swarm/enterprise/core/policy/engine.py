"""
Policy Engine - Dynamic policy evaluation with feature flags and real-time updates.
"""

import threading
import time
import uuid
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Policy Models
# =============================================================================

class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    INDETERMINATE = "indeterminate"
    NOT_APPLICABLE = "not_applicable"


class AttributeType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    MAP = "map"
    TIMESTAMP = "timestamp"


@dataclass
class Attribute:
    """A policy attribute."""
    name: str
    attr_type: AttributeType
    value: Any = None
    category: str = "custom"  # subject, resource, action, environment, custom
    description: str = ""
    required: bool = False


@dataclass
class PolicyCondition:
    """A single condition in a policy rule."""
    condition_id: str = field(default_factory=lambda: f"cond-{uuidv7()}")
    attribute: str = ""
    operator: str = "eq"  # eq, ne, gt, gte, lt, lte, in, not_in, contains, starts_with, ends_with, regex
    value: Any = None
    attributes: List[str] = field(default_factory=list)  # For multi-attribute conditions


@dataclass
class PolicyRule:
    """A single policy rule."""
    rule_id: str = field(default_factory=lambda: f"rule-{uuidv7()}")
    name: str = ""
    description: str = ""
    effect: PolicyEffect = PolicyEffect.ALLOW
    conditions: List[PolicyCondition] = field(default_factory=list)
    enabled: bool = True
    priority: int = 100
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Policy:
    """A complete policy with multiple rules."""
    policy_id: str = field(default_factory=lambda: f"pol-{uuidv7()}")
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    rules: List[PolicyRule] = field(default_factory=list)
    enabled: bool = True
    target: str = "",
    priority: int = 100  # What this policy applies to (e.g., "api", "resource", "action")
    combining_algorithm: str = "first_applicable"  # first_applicable, deny_overrides, allow_overrides
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    tags: Set[str] = field(default_factory=set)


@dataclass
class EvaluationContext:
    """Context for policy evaluation."""
    subject: Dict[str, Any] = field(default_factory=dict)
    resource: Dict[str, Any] = field(default_factory=dict)
    action: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)
    
    def get_attribute(self, category: str, name: str) -> Any:
        """Get attribute value by category and name."""
        category_map = {
            "subject": self.subject,
            "resource": self.resource,
            "action": self.action,
            "environment": self.environment,
        }
        cat_dict = category_map.get(category, {})
        return cat_dict.get(name)


@dataclass
class PolicyEvaluationResult:
    """Result of policy evaluation."""
    policy_id: str
    decision: PolicyDecision
    matched_rules: List[str] = field(default_factory=list)
    denied_rules: List[str] = field(default_factory=list)
    obligations: List[Dict[str, Any]] = field(default_factory=list)
    advice: List[Dict[str, Any]] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evaluation_time_ms: float = 0.0


# =============================================================================
# Condition Evaluator
# =============================================================================

class ConditionEvaluator:
    """Evaluates policy conditions against context."""
    
    @staticmethod
    def evaluate(condition: PolicyCondition, context: EvaluationContext) -> bool:
        """Evaluate a single condition."""
        # Get attribute value from context
        attr_value = context.get_attribute("resource", condition.attribute)
        if attr_value is None:
            attr_value = context.get_attribute("subject", condition.attribute)
        if attr_value is None:
            attr_value = context.get_attribute("action", condition.attribute)
        if attr_value is None:
            attr_value = context.get_attribute("environment", condition.attribute)
        
        if attr_value is None:
            return False
        
        return ConditionEvaluator._compare(attr_value, condition.operator, condition.value)
    
    @staticmethod
    def _compare(actual: Any, operator: str, expected: Any) -> bool:
        """Compare actual value against expected using operator."""
        try:
            if operator in ("eq", "=="):
                return actual == expected
            elif operator in ("ne", "!="):
                return actual != expected
            elif operator in ("gt", ">"):
                return float(actual) > float(expected)
            elif operator in ("gte", ">="):
                return float(actual) >= float(expected)
            elif operator in ("lt", "<"):
                return float(actual) < float(expected)
            elif operator in ("lte", "<="):
                return float(actual) <= float(expected)
            elif operator in ("in",):
                return actual in (expected if isinstance(expected, list) else [expected])
            elif operator in ("not_in",):
                return actual not in (expected if isinstance(expected, list) else [expected])
            elif operator in ("contains",):
                return str(expected) in str(actual)
            elif operator in ("starts_with",):
                return str(actual).startswith(str(expected))
            elif operator in ("ends_with",):
                return str(actual).endswith(str(expected))
            elif operator in ("regex",):
                import re
                return bool(re.match(str(expected), str(actual)))
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
        except (ValueError, TypeError) as e:
            logger.error(f"Comparison error: {e}")
            return False


# =============================================================================
# Policy Engine
# =============================================================================

class PolicyEngine:
    """Core policy evaluation engine."""
    
    def __init__(self):
        self._policies: Dict[str, Policy] = {}
        self._lock = threading.RLock()
        self._condition_evaluator = ConditionEvaluator()
    
    def add_policy(self, policy: Policy) -> None:
        """Add a policy."""
        with self._lock:
            self._policies[policy.policy_id] = policy
            logger.info(f"Added policy: {policy.policy_id} ({policy.name})")
    
    def remove_policy(self, policy_id: str) -> bool:
        """Remove a policy."""
        with self._lock:
            if policy_id in self._policies:
                del self._policies[policy_id]
                logger.info(f"Removed policy: {policy_id}")
                return True
            return False
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        with self._lock:
            return self._policies.get(policy_id)
    
    def list_policies(self, enabled_only: bool = True, target: Optional[str] = None) -> List[Policy]:
        """List policies."""
        with self._lock:
            policies = list(self._policies.values())
            
            if enabled_only:
                policies = [p for p in policies if p.enabled]
            if target:
                policies = [p for p in policies if p.target == target]
            
            return policies
    
    def update_policy(self, policy_id: str, updates: Dict[str, Any]) -> Optional[Policy]:
        """Update a policy."""
        with self._lock:
            policy = self._policies.get(policy_id)
            if not policy:
                return None
            
            for key, value in updates.items():
                if hasattr(policy, key) and key not in ("policy_id", "created_at", "created_by"):
                    setattr(policy, key, value)
            
            policy.updated_at = now_utc()
            logger.info(f"Updated policy: {policy_id}")
            return policy
    
    def evaluate(
        self,
        context: EvaluationContext,
        target: Optional[str] = None,
    ) -> PolicyEvaluationResult:
        """Evaluate policies against context."""
        start_time = time.time()
        
        with self._lock:
            applicable_policies = [
                p for p in self._policies.values()
                if p.enabled and (not target or p.target == target)
            ]
            
            # Sort by priority
            applicable_policies.sort(key=lambda p: p.priority)
        
        if not applicable_policies:
            return PolicyEvaluationResult(
                policy_id="",
                decision=PolicyDecision.NOT_APPLICABLE,
                evaluation_time_ms=(time.time() - start_time) * 1000,
            )
        
        # Evaluate each policy
        for policy in applicable_policies:
            result = self._evaluate_policy(policy, context)
            if result.decision != PolicyDecision.NOT_APPLICABLE:
                result.evaluation_time_ms = (time.time() - start_time) * 1000
                return result
        
        return PolicyEvaluationResult(
            policy_id="",
            decision=PolicyDecision.NOT_APPLICABLE,
            evaluation_time_ms=(time.time() - start_time) * 1000,
        )
    
    def _evaluate_policy(self, policy: Policy, context: EvaluationContext) -> PolicyEvaluationResult:
        """Evaluate a single policy."""
        matched_rules = []
        denied_rules = []
        
        for rule in policy.rules:
            if not rule.enabled:
                continue
            
            rule_matched = True
            for condition in rule.conditions:
                if not ConditionEvaluator.evaluate(condition, self._create_eval_context(rule)):
                    rule_matched = False
                    break
            
            if rule_matched:
                if rule.effect == PolicyEffect.ALLOW:
                    matched_rules.append(rule.rule_id)
                    return PolicyEvaluationResult(
                        policy_id=policy.policy_id,
                        decision=PolicyDecision.ALLOW,
                        matched_rules=matched_rules,
                    )
                elif rule.effect == PolicyEffect.DENY:
                    denied_rules.append(rule.rule_id)
                    return PolicyEvaluationResult(
                        policy_id=policy.policy_id,
                        decision=PolicyDecision.DENY,
                        denied_rules=denied_rules,
                    )
        
        return PolicyEvaluationResult(
            policy_id=policy.policy_id,
            decision=PolicyDecision.NOT_APPLICABLE,
        )
    
    def _create_eval_context(self, rule: PolicyRule) -> EvaluationContext:
        """Create evaluation context for rule (simplified)."""
        return EvaluationContext()


# =============================================================================
# Feature Flag System
# =============================================================================

class FlagType(str, Enum):
    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    JSON = "json"


@dataclass
class FeatureFlag:
    """A feature flag with targeting rules."""
    flag_id: str = field(default_factory=lambda: f"flag-{uuidv7()}")
    name: str = ""
    description: str = ""
    flag_type: FlagType = FlagType.BOOLEAN
    default_value: Any = False
    enabled: bool = True
    
    # Targeting rules
    targeting_rules: List[Dict[str, Any]] = field(default_factory=list)
    # Example: [{"attribute": "user.country", "operator": "in", "value": ["US", "CA"], "percentage": 100}]
    
    # Rollout
    rollout_percentage: float = 100.0
    variants: Dict[str, Any] = field(default_factory=dict)  # For multivariate flags
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    tags: Set[str] = field(default_factory=set)
    
    def evaluate(self, context: Dict[str, Any]) -> Any:
        """Evaluate flag for given context."""
        if not self.enabled:
            return self.default_value
        
        # Check targeting rules
        for rule in self.targeting_rules:
            if self._matches_rule(rule, context):
                # Check percentage rollout
                if rule.get("percentage", 100) < 100:
                    # Use consistent hashing for consistent assignment
                    user_key = str(context.get(rule.get("hash_key", "user_id"), "anonymous"))
                    hash_val = hash(f"{self.flag_id}:{rule.get('hash_key', 'user_id')}:{user_key}") % 100
                    if hash_val >= rule.get("percentage", 100):
                        continue
                
                # Return variant or value
                if "value" in rule:
                    return rule["value"]
                if self.variants and "variant" in rule:
                    return self.variants.get(rule["variant"], self.default_value)
        
        # Check default rollout
        if self.rollout_percentage < 100:
            hash_val = hash(f"{self.flag_id}:default") % 100
            if hash_val >= self.rollout_percentage:
                return self.default_value
        
        return self.default_value
    
    def _matches_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if context matches targeting rule."""
        conditions = rule.get("conditions", [])
        for cond in rule.get("conditions", []):
            attr = cond.get("attribute")
            operator = cond.get("operator", "eq")
            value = cond.get("value")
            
            # Get value from context
            actual = context.get(attr)
            if actual is None:
                return False
            
            # Simple comparison
            if cond.get("operator") == "eq" and actual != value:
                return False
            elif cond.get("operator") == "in" and actual not in value:
                return False
            elif cond.get("operator") == "not_in" and actual in value:
                return False
        
        return True


class FeatureFlagStore:
    """Manages feature flags with real-time updates."""
    
    def __init__(self):
        self._flags: Dict[str, FeatureFlag] = {}
        self._lock = threading.RLock()
        
        # Change listeners
        self._listeners: List[Callable[[FeatureFlag, str], None]] = []
    
    def create_flag(self, flag: FeatureFlag) -> FeatureFlag:
        """Create a new feature flag."""
        with self._lock:
            self._flags[flag.flag_id] = flag
            self._notify_listeners(flag, "created")
            logger.info(f"Created feature flag: {flag.flag_id} ({flag.name})")
            return flag
    
    def get_flag(self, flag_id: str) -> Optional[FeatureFlag]:
        """Get a feature flag."""
        with self._lock:
            return self._flags.get(flag_id)
    
    def get_flag_by_name(self, name: str) -> Optional[FeatureFlag]:
        """Get a feature flag by name."""
        with self._lock:
            for flag in self._flags.values():
                if flag.name == name:
                    return flag
            return None
    
    def list_flags(self, enabled_only: bool = True) -> List[FeatureFlag]:
        """List all feature flags."""
        with self._lock:
            flags = list(self._flags.values())
            if enabled_only:
                flags = [f for f in flags if f.enabled]
            return flags
    
    def update_flag(self, flag_id: str, updates: Dict[str, Any]) -> Optional[FeatureFlag]:
        """Update a feature flag."""
        with self._lock:
            flag = self._flags.get(flag_id)
            if not flag:
                return None
            
            for key, value in updates.items():
                if hasattr(flag, key) and key not in ("flag_id", "created_at", "created_by"):
                    setattr(flag, key, value)
            
            flag.updated_at = now_utc()
            self._notify_listeners(flag, "updated")
            logger.info(f"Updated feature flag: {flag_id}")
            return flag
    
    def delete_flag(self, flag_id: str) -> bool:
        """Delete a feature flag."""
        with self._lock:
            if flag_id in self._flags:
                del self._flags[flag_id]
                logger.info(f"Deleted feature flag: {flag_id}")
                return True
            return False
    
    def evaluate_flag(self, flag_id: str, context: Dict[str, Any]) -> Any:
        """Evaluate a flag for a context."""
        with self._lock:
            flag = self._flags.get(flag_id)
            if not flag:
                return None
            return flag.evaluate(context)
    
    def add_listener(self, listener: Callable[[FeatureFlag, str], None]) -> None:
        """Add a change listener."""
        self._listeners.append(listener)
    
    def _notify_listeners(self, flag: FeatureFlag, event: str) -> None:
        for listener in self._listeners:
            try:
                listener(flag, event)
            except Exception as e:
                logger.error(f"Flag listener error: {e}")


# =============================================================================
# Policy Engine with Feature Flags
# =============================================================================

class PolicyEngineWithFlags:
    """Policy engine integrated with feature flags."""
    
    def __init__(self):
        self.policy_engine = PolicyEngine()
        self.flag_store = FeatureFlagStore()
        self._lock = threading.RLock()
    
    def evaluate(
        self,
        context: EvaluationContext,
        flag_context: Optional[Dict[str, Any]] = None,
    ) -> PolicyEvaluationResult:
        """Evaluate policies with feature flag awareness."""
        # Evaluate feature flags first
        flag_results = {}
        if flag_context:
            for flag in self.flag_store.list_flags():
                flag_results[flag.flag_id] = flag.evaluate(flag_context)
        
        # Add flag results to context
        context.environment["feature_flags"] = flag_results
        
        return self.policy_engine.evaluate(context)
    
    def is_feature_enabled(self, flag_name: str, context: Dict[str, Any]) -> bool:
        """Check if a feature is enabled for context."""
        flag = self.flag_store.get_flag_by_name(flag_name)
        if not flag:
            return False
        return bool(flag.evaluate(context))
    
    def get_flag_value(self, flag_name: str, context: Dict[str, Any]) -> Any:
        """Get feature flag value for context."""
        flag = self.flag_store.get_flag_by_name(flag_name)
        if not flag:
            return None
        return flag.evaluate(context)


# =============================================================================
# Policy Builder
# =============================================================================

class PolicyBuilder:
    """Fluent builder for creating policies."""
    
    def __init__(self, policy_id: str, name: str, target: str = "",
    priority: int = 100):
        self.policy = Policy(
            policy_id=policy_id,
            name=name,
            target=target,
        )
    
    def description(self, desc: str) -> "PolicyBuilder":
        self.policy.description = desc
        return self
    
    def version(self, version: str) -> "PolicyBuilder":
        self.policy.version = version
        return self
    
    def combining_algorithm(self, algorithm: str) -> "PolicyBuilder":
        self.policy.combining_algorithm = algorithm
        return self
    
    def add_rule(
        self,
        name: str,
        effect: PolicyEffect,
        conditions: List[Dict[str, Any]],
        priority: int = 100,
    ) -> "PolicyBuilder":
        conditions = [
            PolicyCondition(
                attribute=c.get("attribute", ""),
                operator=c.get("operator", "eq"),
                value=c.get("value"),
            )
            for c in conditions
        ]
        
        rule = PolicyRule(
            name=name,
            effect=effect,
            conditions=conditions,
            priority=priority,
        )
        self.policy.rules.append(rule)
        return self
    
    def target(self, target: str) -> "PolicyBuilder":
        self.policy.target = target
        return self
    
    def tags(self, tags: Set[str]) -> "PolicyBuilder":
        self.policy.tags = tags
        return self
    
    def build(self) -> Policy:
        # Sort rules by priority
        self.policy.rules.sort(key=lambda r: r.priority)
        return self.policy


class FeatureFlagBuilder:
    """Fluent builder for creating feature flags."""
    
    def __init__(self, flag_id: str, name: str):
        self.flag = FeatureFlag(
            flag_id=flag_id,
            name=name,
        )
    
    def description(self, desc: str) -> "FeatureFlagBuilder":
        self.flag.description = desc
        return self
    
    def type(self, flag_type: FlagType) -> "FeatureFlagBuilder":
        self.flag.flag_type = flag_type
        return self
    
    def default_value(self, value: Any) -> "FeatureFlagBuilder":
        self.flag.default_value = value
        return self
    
    def add_targeting_rule(
        self,
        conditions: List[Dict[str, Any]],
        value: Any = None,
        percentage: float = 100.0,
        hash_key: str = "user_id",
    ) -> "FeatureFlagBuilder":
        rule = {
            "conditions": conditions,
            "value": value,
            "percentage": percentage,
            "hash_key": "user_id",
        }
        self.flag.targeting_rules.append(rule)
        return self
    
    def rollout(self, percentage: float) -> "FeatureFlagBuilder":
        self.flag.rollout_percentage = percentage
        return self
    
    def add_variant(self, variant_name: str, value: Any) -> "FeatureFlagBuilder":
        self.flag.variants[variant_name] = value
        return self
    
    def tags(self, tags: Set[str]) -> "FeatureFlagBuilder":
        self.flag.tags = tags
        return self
    
    def build(self) -> FeatureFlag:
        return self.flag


# =============================================================================
# Factory
# =============================================================================

def create_policy_engine() -> PolicyEngine:
    """Create a policy engine."""
    return PolicyEngine()


def create_feature_flag_store() -> FeatureFlagStore:
    """Create a feature flag store."""
    return FeatureFlagStore()


def create_policy_engine_with_flags() -> PolicyEngineWithFlags:
    """Create a policy engine with feature flags."""
    return PolicyEngineWithFlags()


def create_policy(
    policy_id: str,
    name: str,
    target: str = "",
    priority: int = 100,
    rules: Optional[List[Dict[str, Any]]] = None,
) -> Policy:
    """Create a policy from simple definition."""
    builder = PolicyBuilder(policy_id, name, target)
    
    if rules:
        for rule_def in rules:
            builder.add_rule(
                name=rule_def.get("name", ""),
                effect=PolicyEffect(rule_def.get("effect", "allow")),
                conditions=rule_def.get("conditions", []),
                priority=rule_def.get("priority", 100),
            )
    
    return builder.build()


def create_feature_flag(
    flag_id: str,
    name: str,
    default_value: Any = False,
    flag_type: FlagType = FlagType.BOOLEAN,
) -> FeatureFlag:
    """Create a feature flag."""
    return FeatureFlag(
        flag_id=flag_id,
        name=name,
        default_value=default_value,
        flag_type=flag_type,
    )


# =============================================================================
# Singleton Factory Functions
# =============================================================================

_policy_engine_instance: Optional[PolicyEngine] = None
_flag_store_instance: Optional[FeatureFlagStore] = None
_policy_engine_with_flags_instance: Optional[PolicyEngineWithFlags] = None


def get_policy_engine() -> PolicyEngine:
    """Get singleton policy engine."""
    global _policy_engine_instance
    if _policy_engine_instance is None:
        _policy_engine_instance = create_policy_engine()
    return _policy_engine_instance


def get_feature_flag_store() -> FeatureFlagStore:
    """Get singleton feature flag store."""
    global _flag_store_instance
    if _flag_store_instance is None:
        _flag_store_instance = create_feature_flag_store()
    return _flag_store_instance


def get_policy_engine_with_flags() -> PolicyEngineWithFlags:
    """Get singleton policy engine with flags."""
    global _policy_engine_with_flags_instance
    if _policy_engine_with_flags_instance is None:
        _policy_engine_with_flags_instance = create_policy_engine_with_flags()
    return _policy_engine_with_flags_instance

# Add PolicyContext alias for backward compatibility
PolicyContext = EvaluationContext

# Export PolicyDecision (already defined as enum above)
