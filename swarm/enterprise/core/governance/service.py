"""
Governance Service - Policy evaluation, compliance checking, audit logging.
"""

import hashlib
import json
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict
import logging

from .models import (
    Policy, PolicyRule, PolicyType, PolicyScope, PolicyAction, PolicyEvaluation,
    ComplianceFramework, ComplianceStatus, ComplianceControl, ComplianceCheck, ComplianceReport,
    AuditEvent, AuditEventType, AuditSeverity,
    Risk, RiskLevel,
    now_utc, uuidv7,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Policy Engine
# =============================================================================

class PolicyEngine:
    """Evaluates policies against request context."""
    
    def __init__(self):
        self._policies: Dict[str, Policy] = {}
        self._lock = threading.RLock()
        self._cel_enabled = False
        self._init_default_policies()
    
    def _init_default_policies(self) -> None:
        """Initialize default governance policies."""
        # Cost control policy
        self.register_policy(Policy(
            policy_id="pol-cost-control",
            name="Cost Control",
            description="Enforce budget limits per tenant",
            policy_type=PolicyType.COST_CONTROL,
            scope=PolicyScope.GLOBAL,
            rules=[
                PolicyRule(
                    name="daily_budget_limit",
                    description="Block requests exceeding daily budget",
                    condition="cost_estimate.daily_total > budget.daily_limit",
                    action=PolicyAction.DENY,
                    severity="high",
                ),
                PolicyRule(
                    name="monthly_budget_warning",
                    description="Warn when approaching monthly budget",
                    condition="cost_estimate.monthly_total > budget.monthly_limit * 0.8",
                    action=PolicyAction.WARN,
                    severity="medium",
                ),
            ],
            priority=10,
        ))
        
        # Data protection policy
        self.register_policy(Policy(
            policy_id="pol-data-protection",
            name="Data Protection",
            description="Prevent PII exposure and enforce encryption",
            policy_type=PolicyType.DATA_PROTECTION,
            scope=PolicyScope.GLOBAL,
            rules=[
                PolicyRule(
                    name="pii_detection",
                    description="Block requests containing PII in logs",
                    condition="contains_pii(request.payload)",
                    action=PolicyAction.DENY,
                    severity="critical",
                ),
                PolicyRule(
                    name="encryption_required",
                    description="Require encryption for sensitive data",
                    condition="data_classification == 'sensitive' and not encryption.enabled",
                    action=PolicyAction.DENY,
                    severity="high",
                ),
            ],
            priority=20,
        ))
        
        # Security policy
        self.register_policy(Policy(
            policy_id="pol-security",
            name="Security Requirements",
            description="Enforce authentication and authorization",
            policy_type=PolicyType.SECURITY,
            scope=PolicyScope.GLOBAL,
            rules=[
                PolicyRule(
                    name="auth_required",
                    description="All requests must have valid authentication",
                    condition="not auth.valid",
                    action=PolicyAction.DENY,
                    severity="critical",
                ),
                PolicyRule(
                    name="admin_approval_sensitive",
                    description="Sensitive operations require admin approval",
                    condition="action.sensitivity == 'high' and not approval.granted",
                    action=PolicyAction.ESCALATE,
                    severity="high",
                ),
            ],
            priority=30,
        ))
        
        # Operational policy
        self.register_policy(Policy(
            policy_id="pol-operational",
            name="Operational Limits",
            description="Enforce rate limits and quotas",
            policy_type=PolicyType.OPERATIONAL,
            scope=PolicyScope.GLOBAL,
            rules=[
                PolicyRule(
                    name="rate_limit",
                    description="Enforce per-tenant rate limits",
                    condition="rate.current > rate.limit",
                    action=PolicyAction.DENY,
                    severity="high",
                ),
                PolicyRule(
                    name="concurrent_jobs",
                    description="Limit concurrent jobs per tenant",
                    condition="jobs.active > quota.max_concurrent",
                    action=PolicyAction.QUEUE,
                    severity="medium",
                ),
            ],
            priority=40,
        ))
    
    def register_policy(self, policy: Policy) -> None:
        """Register a policy."""
        with self._lock:
            self._policies[policy.policy_id] = policy
            logger.info(f"Registered policy: {policy.policy_id} ({policy.name})")
    
    def unregister_policy(self, policy_id: str) -> bool:
        """Unregister a policy."""
        with self._lock:
            if policy_id in self._policies:
                del self._policies[policy_id]
                logger.info(f"Unregistered policy: {policy_id}")
                return True
            return False
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        with self._lock:
            return self._policies.get(policy_id)
    
    def list_policies(
        self,
        policy_type: Optional[Any] = None,
        scope: Optional[Any] = None,
        enabled_only: bool = True,
    ) -> List[Policy]:
        """List policies with filters."""
        with self._lock:
            policies = list(self._policies.values())
            
            if enabled_only:
                policies = [p for p in policies if p.enabled]
            if policy_type:
                policies = [p for p in policies if p.policy_type == policy_type]
            if scope:
                policies = [p for p in policies if p.scope == scope]
            
            # Sort by priority
            policies.sort(key=lambda p: p.priority)
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
            policy.version += 1
            logger.info(f"Updated policy: {policy_id} v{policy.version}")
            return policy
    
    def evaluate(
        self,
        context: Dict[str, Any],
        tenant_id: str = "default",
    ) -> List[PolicyEvaluation]:
        """Evaluate all applicable policies against context."""
        with self._lock:
            # Add tenant to context
            eval_context = {**context, "tenant_id": tenant_id}
            
            applicable = [
                p for p in self._policies.values()
                if p.enabled and p.matches(eval_context)
            ]
            
            results = []
            for policy in applicable:
                evaluation = self._evaluate_policy(policy, eval_context)
                results.append(evaluation)
            
            return results
    
    def _evaluate_policy(self, policy: Policy, context: Dict[str, Any]) -> PolicyEvaluation:
        """Evaluate a single policy."""
        rule_results = []
        final_action = PolicyAction.ALLOW
        violations = []
        
        for rule in policy.rules:
            try:
                # Simple condition evaluation (can be extended with CEL/JSON Logic)
                matched = self._evaluate_condition(rule.condition, context)
                
                rule_results.append({
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "matched": matched,
                    "action": rule.action.value,
                    "severity": rule.severity,
                })
                
                if matched:
                    violations.append(f"{rule.name}: {rule.description}")
                    # Most restrictive action wins
                    if self._action_severity(rule.action) > self._action_severity(final_action):
                        final_action = rule.action
                        
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
                rule_results.append({
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "matched": False,
                    "error": str(e),
                })
        
        return PolicyEvaluation(
            policy_id=policy.policy_id,
            policy_name=policy.name,
            matched=len(violations) > 0,
            rule_results=rule_results,
            final_action=final_action,
            violations=violations,
        )
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a policy condition.
        
        Simple implementation - can be extended with CEL (Common Expression Language)
        or JSON Logic for complex conditions.
        """
        if not condition:
            return False
        
        # Simple keyword-based matching for demo
        # In production, use cel-go or similar
        condition_lower = condition.lower()
        
        # Check for budget conditions
        if "budget" in condition_lower:
            budget_limit = context.get("budget_limit", float("inf"))
            cost_estimate = context.get("cost_estimate", 0)
            if cost_estimate > budget_limit:
                return True
        
        # Check for PII
        if "pii" in condition_lower or "contains_pii" in condition_lower:
            return context.get("contains_pii", False)
        
        # Check for auth
        if "auth.valid" in condition_lower:
            return not context.get("auth_valid", True)
        
        # Check for rate limits
        if "rate.current" in condition_lower and "rate.limit" in condition_lower:
            current = context.get("rate_current", 0)
            limit = context.get("rate_limit", float("inf"))
            return current > limit
        
        # Check for sensitive action
        if "sensitivity" in condition_lower:
            return context.get("action_sensitivity", "low") == "high"
        
        # Check for approval
        if "approval.granted" in condition_lower:
            return not context.get("approval_granted", False)
        
        return False
    
    def _action_severity(self, action: PolicyAction) -> int:
        """Get severity order for actions."""
        order = {
            PolicyAction.ALLOW: 0,
            PolicyAction.AUDIT: 1,
            PolicyAction.WARN: 2,
            PolicyAction.QUEUE: 3,
            PolicyAction.ESCALATE: 4,
            PolicyAction.DENY: 5,
            PolicyAction.QUARANTINE: 6,
        }
        return order.get(action, 0)
    
    def get_final_decision(self, evaluations: List[PolicyEvaluation]) -> Dict[str, Any]:
        """Get final decision from all evaluations."""
        if not evaluations:
            return {"action": PolicyAction.ALLOW.value, "violations": [], "policies": []}
        
        # Most restrictive action wins
        max_severity = 0
        final_action = PolicyAction.ALLOW
        all_violations = []
        policy_names = []
        
        for eval in evaluations:
            policy_names.append(eval.policy_name)
            all_violations.extend(eval.violations)
            severity = self._action_severity(eval.final_action)
            if severity > max_severity:
                max_severity = severity
                final_action = eval.final_action
        
        return {
            "action": final_action.value,
            "violations": all_violations,
            "policies": policy_names,
            "evaluations": [
                {
                    "policy": e.policy_name,
                    "matched": e.matched,
                    "action": e.final_action.value,
                    "violations": e.violations,
                }
                for e in evaluations
            ],
        }


# =============================================================================
# Compliance Engine
# =============================================================================

class ComplianceEngine:
    """Manages compliance frameworks and automated checks."""
    
    def __init__(self):
        self._frameworks: Dict[ComplianceFramework, List[ComplianceControl]] = {}
        self._checks: Dict[str, ComplianceCheck] = {}
        self._reports: Dict[str, ComplianceReport] = {}
        self._lock = threading.RLock()
        self._load_default_frameworks()
    
    def _load_default_frameworks(self) -> None:
        """Load default compliance frameworks."""
        # GDPR Controls
        self._frameworks[ComplianceFramework.GDPR] = [
            ComplianceControl(
                control_id="gdpr-art5",
                framework=ComplianceFramework.GDPR,
                title="Lawfulness, fairness and transparency",
                description="Personal data processed lawfully, fairly, transparently",
                category="principles",
                requirements=["Legal basis documented", "Privacy notice provided"],
                evidence_required=["Privacy policy", "Legal basis records"],
                automated_check=True,
            ),
            ComplianceControl(
                control_id="gdpr-art25",
                framework=ComplianceFramework.GDPR,
                title="Data protection by design and by default",
                description="Implement appropriate technical and organisational measures",
                category="technical_measures",
                requirements=["Privacy by design", "Data minimization", "Default protection"],
                evidence_required=["DPIA records", "System architecture docs"],
                automated_check=True,
            ),
            ComplianceControl(
                control_id="gdpr-art32",
                framework=ComplianceFramework.GDPR,
                title="Security of processing",
                description="Implement appropriate technical and organisational measures",
                category="security",
                requirements=["Encryption", "Access controls", "Incident response"],
                evidence_required=["Security policies", "Penetration test reports"],
                automated_check=True,
            ),
        ]
        
        # SOC2 Controls
        self._frameworks[ComplianceFramework.SOC2] = [
            ComplianceControl(
                control_id="soc2-cc6",
                framework=ComplianceFramework.SOC2,
                title="Logical Access Controls",
                description="Restrict logical access to systems and data",
                category="access_control",
                requirements=["MFA", "Least privilege", "Regular access reviews"],
                evidence_required=["Access control matrix", "Review records"],
                automated_check=True,
            ),
            ComplianceControl(
                control_id="soc2-cc7",
                framework=ComplianceFramework.SOC2,
                title="System Monitoring",
                description="Monitor system for anomalies and incidents",
                category="monitoring",
                requirements=["SIEM", "Alerting", "Incident response"],
                evidence_required=["Monitoring configs", "Incident logs"],
                automated_check=True,
            ),
        ]
    
    def get_controls(self, framework: ComplianceFramework) -> List[ComplianceControl]:
        """Get controls for a framework."""
        with self._lock:
            return self._frameworks.get(framework, [])
    
    def run_check(
        self,
        control: ComplianceControl,
        context: Dict[str, Any],
        tenant_id: str = "default",
    ) -> ComplianceCheck:
        """Run a compliance check."""
        check = ComplianceCheck(
            control_id=control.control_id,
            framework=control.framework,
        )
        
        try:
            if control.automated_check and control.check_script:
                # Execute automated check
                result = self._run_automated_check(control, context)
                check.status = result.get("status", ComplianceStatus.COMPLIANT)
                check.score = result.get("score", 1.0)
                check.findings = result.get("findings", [])
                check.evidence = result.get("evidence", [])
                check.remediation = result.get("remediation")
            else:
                # Manual check - mark as not assessed
                check.status = ComplianceStatus.NOT_ASSESSED
                check.score = 0.0
                check.findings = ["Manual review required"]
            
        except Exception as e:
            logger.error(f"Compliance check failed for {control.control_id}: {e}")
            check.status = ComplianceStatus.NON_COMPLIANT
            check.score = 0.0
            check.findings = [f"Check error: {e}"]
        
        check.checked_at = now_utc()
        check.next_check_due = now_utc() + timedelta(days=90)
        
        with self._lock:
            self._checks[check.check_id] = check
        
        return check
    
    def _run_automated_check(
        self,
        control: ComplianceControl,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run automated compliance check."""
        # Placeholder - in production, execute actual check scripts
        check_type = control.control_id.split("-")[1] if "-" in control.control_id else "generic"
        
        if "encryption" in control.title.lower():
            return {
                "status": ComplianceStatus.COMPLIANT if context.get("encryption_enabled") else ComplianceStatus.NON_COMPLIANT,
                "score": 1.0 if context.get("encryption_enabled") else 0.0,
                "findings": [] if context.get("encryption_enabled") else ["Encryption not enabled"],
            }
        elif "access" in control.title.lower():
            return {
                "status": ComplianceStatus.COMPLIANT if context.get("mfa_enabled") else ComplianceStatus.PARTIAL,
                "score": 1.0 if context.get("mfa_enabled") else 0.5,
                "findings": [] if context.get("mfa_enabled") else ["MFA not enforced"],
            }
        elif "monitoring" in control.title.lower():
            return {
                "status": ComplianceStatus.COMPLIANT if context.get("siem_enabled") else ComplianceStatus.NON_COMPLIANT,
                "score": 1.0 if context.get("siem_enabled") else 0.0,
                "findings": [] if context.get("siem_enabled") else ["SIEM not configured"],
            }
        
        return {
            "status": ComplianceStatus.COMPLIANT,
            "score": 1.0,
            "findings": [],
        }
    
    def generate_report(
        self,
        tenant_id: str,
        framework: ComplianceFramework,
    ) -> ComplianceReport:
        """Generate compliance report for tenant."""
        controls = self.get_controls(framework)
        checks = []
        
        for control in controls:
            check = self.run_check(control, {"tenant_id": tenant_id}, tenant_id)
            checks.append(check)
        
        # Calculate overall
        if checks:
            compliant = sum(1 for c in checks if c.status == ComplianceStatus.COMPLIANT)
            total = len(checks)
            overall_score = sum(c.score for c in checks) / total
            
            if compliant == total:
                overall_status = ComplianceStatus.COMPLIANT
            elif compliant == 0:
                overall_status = ComplianceStatus.NON_COMPLIANT
            else:
                overall_status = ComplianceStatus.PARTIAL
        else:
            overall_status = ComplianceStatus.NOT_ASSESSED
            overall_score = 0.0
        
        report = ComplianceReport(
            tenant_id=tenant_id,
            framework=framework,
            overall_status=overall_status,
            overall_score=overall_score,
            checks=checks,
            valid_until=now_utc() + timedelta(days=30),
        )
        
        with self._lock:
            self._reports[report.report_id] = report
        
        return report
    
    def get_report(self, report_id: str) -> Optional[ComplianceReport]:
        """Get a compliance report."""
        with self._lock:
            return self._reports.get(report_id)


# =============================================================================
# Audit Logger
# =============================================================================

class AuditLogger:
    """Immutable audit event logging with cryptographic chaining."""
    
    def __init__(self, storage: Optional[Any] = None):
        self._events: List[AuditEvent] = []
        self._storage = storage
        self._lock = threading.RLock()
        self._last_hash: Optional[str] = None
    
    def log(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        tenant_id: str,
        actor_id: str,
        actor_type: str,
        action: str,
        outcome: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> AuditEvent:
        """Log an audit event."""
        with self._lock:
            event = AuditEvent(
                event_type=event_type,
                severity=severity,
                tenant_id=tenant_id,
                actor_id=actor_id,
                actor_type=actor_type,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                outcome=outcome,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            
            # Cryptographic chaining
            event.previous_hash = self._last_hash
            event.event_hash = self._compute_hash(event)
            self._last_hash = event.event_hash
            
            self._events.append(event)
            
            # Persist to storage if available
            if self._storage:
                try:
                    self._storage.save_event(event)
                except Exception as e:
                    logger.error(f"Failed to persist audit event: {e}")
            
            return event
    
    def _compute_hash(self, event: AuditEvent) -> str:
        """Compute cryptographic hash of event."""
        data = f"{event.event_id}{event.timestamp.isoformat()}{event.previous_hash or ''}{json.dumps(event.to_dict(), sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def query(
        self,
        tenant_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        actor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[AuditSeverity] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Query audit events."""
        with self._lock:
            events = self._events
            
            if tenant_id:
                events = [e for e in events if e.tenant_id == tenant_id]
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            if actor_id:
                events = [e for e in events if e.actor_id == actor_id]
            if start_time:
                events = [e for e in events if e.timestamp >= start_time]
            if end_time:
                events = [e for e in events if e.timestamp <= end_time]
            if severity:
                events = [e for e in events if e.severity == severity]
            
            events.sort(key=lambda e: e.timestamp, reverse=True)
            return events[:limit]
    
    def verify_integrity(self) -> Dict[str, Any]:
        """Verify cryptographic integrity of audit chain."""
        with self._lock:
            if not self._events:
                return {"valid": True, "checked": 0}
            
            prev_hash = None
            valid = True
            errors = []
            
            for i, event in enumerate(self._events):
                # Verify previous hash
                if event.previous_hash != prev_hash:
                    valid = False
                    errors.append(f"Event {i}: previous_hash mismatch")
                
                # Verify event hash
                computed = self._compute_hash(event)
                if event.event_hash != computed:
                    valid = False
                    errors.append(f"Event {i}: event_hash mismatch")
                
                prev_hash = event.event_hash
            
            return {
                "valid": valid,
                "checked": len(self._events),
                "errors": errors,
            }
    
    def export_chain(self) -> List[Dict[str, Any]]:
        """Export full audit chain for external verification."""
        with self._lock:
            return [e.to_dict() for e in self._events]


# =============================================================================
# Risk Manager
# =============================================================================

class RiskManager:
    """Manages risk assessments and mitigation tracking."""
    
    def __init__(self):
        self._risks: Dict[str, Risk] = {}
        self._lock = threading.RLock()
    
    def assess_risk(
        self,
        title: str,
        description: str,
        category: str,
        likelihood: float,
        impact: float,
        mitigation: Optional[str] = None,
        owner: Optional[str] = None,
        tags: Optional[Set[str]] = None,
    ) -> Risk:
        """Create a risk assessment."""
        risk = Risk(
            title=title,
            description=description,
            category=category,
            likelihood=max(0.0, min(1.0, likelihood)),
            impact=max(0.0, min(1.0, impact)),
            mitigation=mitigation,
            owner=owner,
            tags=tags or set(),
        )
        
        # Auto-determine level
        score = risk.risk_score
        if score >= 0.8:
            risk.level = RiskLevel.CRITICAL
        elif score >= 0.6:
            risk.level = RiskLevel.HIGH
        elif score >= 0.4:
            risk.level = RiskLevel.MEDIUM
        elif score >= 0.2:
            risk.level = RiskLevel.LOW
        else:
            risk.level = RiskLevel.NEGLIGIBLE
        
        with self._lock:
            self._risks[risk.risk_id] = risk
        
        return risk
    
    def get_risk(self, risk_id: str) -> Optional[Risk]:
        """Get a risk by ID."""
        with self._lock:
            return self._risks.get(risk_id)
    
    def list_risks(
        self,
        level: Optional[RiskLevel] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Risk]:
        """List risks with filters."""
        with self._lock:
            risks = list(self._risks.values())
            
            if level:
                risks = [r for r in risks if r.level == level]
            if category:
                risks = [r for r in risks if r.category == category]
            if status:
                risks = [r for r in risks if r.status == status]
            
            # Sort by risk score descending
            risks.sort(key=lambda r: r.risk_score, reverse=True)
            return risks
    
    def mitigate_risk(self, risk_id: str, mitigation: str, owner: str) -> Optional[Risk]:
        """Mark risk as mitigated."""
        with self._lock:
            risk = self._risks.get(risk_id)
            if not risk:
                return None
            
            risk.mitigation = mitigation
            risk.owner = owner
            risk.status = "mitigated"
            risk.mitigated_at = now_utc()
            return risk
    
    def accept_risk(self, risk_id: str, owner: str, justification: str) -> Optional[Risk]:
        """Accept a risk."""
        with self._lock:
            risk = self._risks.get(risk_id)
            if not risk:
                return None
            
            risk.status = "accepted"
            risk.owner = owner
            risk.mitigation = f"ACCEPTED: {justification}"
            return risk
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get risk portfolio summary."""
        with self._lock:
            risks = list(self._risks.values())
            
            by_level = defaultdict(int)
            by_category = defaultdict(int)
            by_status = defaultdict(int)
            
            for r in risks:
                by_level[r.level.value] += 1
                by_category[r.category] += 1
                by_status[r.status] += 1
            
            return {
                "total_risks": len(risks),
                "by_level": dict(by_level),
                "by_category": dict(by_category),
                "by_status": dict(by_status),
                "highest_risk": max(risks, key=lambda r: r.risk_score).risk_id if risks else None,
                "average_score": sum(r.risk_score for r in risks) / len(risks) if risks else 0,
            }


# =============================================================================
# Governance Facade
# =============================================================================

class GovernanceService:
    """Unified governance service combining all components."""
    
    def __init__(self, audit_storage: Optional[Any] = None):
        self.policy_engine = PolicyEngine()
        self.compliance_engine = ComplianceEngine()
        self.audit_logger = AuditLogger(audit_storage)
        self.risk_manager = RiskManager()
        self._lock = threading.RLock()
    
    def evaluate_request(
        self,
        context: Dict[str, Any],
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Evaluate request against all governance policies."""
        evaluations = self.policy_engine.evaluate(context, tenant_id)
        decision = self.policy_engine.get_final_decision(evaluations)
        
        # Audit the evaluation
        self.audit_logger.log(
            event_type=AuditEventType.POLICY_EVALUATED,
            severity=AuditSeverity.INFO,
            tenant_id=tenant_id,
            actor_id=context.get("actor_id", "system"),
            actor_type="system",
            action="policy_evaluation",
            outcome="success" if decision["action"] == "allow" else "denied",
            details={
                "decision": decision,
                "context_keys": list(context.keys()),
            },
        )
        
        return decision
    
    def check_compliance(
        self,
        tenant_id: str,
        framework: ComplianceFramework,
    ) -> ComplianceReport:
        """Run compliance assessment."""
        report = self.compliance_engine.generate_report(tenant_id, framework)
        
        # Audit
        self.audit_logger.log(
            event_type=AuditEventType.COMPLIANCE_CHECKED,
            severity=AuditSeverity.INFO,
            tenant_id=tenant_id,
            actor_id="governance_service",
            actor_type="system",
            action="compliance_assessment",
            outcome="success",
            details={
                "framework": framework.value,
                "report_id": report.report_id,
                "status": report.overall_status.value,
                "score": report.overall_score,
            },
        )
        
        return report
    
    def log_audit(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        tenant_id: str,
        actor_id: str,
        actor_type: str,
        action: str,
        outcome: str,
        **kwargs,
    ) -> AuditEvent:
        """Log an audit event."""
        return self.audit_logger.log(
            event_type=event_type,
            severity=severity,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            outcome=outcome,
            **kwargs,
        )
    
    def assess_risk(
        self,
        title: str,
        description: str,
        category: str,
        likelihood: float,
        impact: float,
        **kwargs,
    ) -> Risk:
        """Assess a new risk."""
        return self.risk_manager.assess_risk(
            title=title,
            description=description,
            category=category,
            likelihood=likelihood,
            impact=impact,
            **kwargs,
        )
    
    def get_dashboard(self, tenant_id: str) -> Dict[str, Any]:
        """Get governance dashboard data."""
        return {
            "policies": {
                "total": len(self.policy_engine.list_policies()),
                "by_type": self._count_policies_by_type(),
            },
            "compliance": {
                "frameworks": [f.value for f in ComplianceFramework],
            },
            "audit": {
                "recent_events": len(self.audit_logger.query(tenant_id=tenant_id, limit=10)),
                "integrity": self.audit_logger.verify_integrity(),
            },
            "risks": self.risk_manager.get_risk_summary(),
        }
    
    def _count_policies_by_type(self) -> Dict[str, int]:
        counts = defaultdict(int)
        for p in self.policy_engine.list_policies():
            counts[p.policy_type.value] += 1
        return dict(counts)


# =============================================================================
# Factory
# =============================================================================

def create_governance_service(audit_storage: Optional[Any] = None) -> GovernanceService:
    """Create a GovernanceService instance."""
    return GovernanceService(audit_storage)
