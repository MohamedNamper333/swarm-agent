"""
Alert Manager Module - Webhook Alert System
Manages alerts based on metrics thresholds and sends webhooks.
"""
import time
import json
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import urllib.request
import urllib.parse

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    """Alert status"""
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"


@dataclass
class AlertRule:
    """A rule that triggers alerts"""
    id: str
    name: str
    description: str
    metric_name: str
    condition: str  # "gt", "lt", "eq", "ne"
    threshold: float
    severity: AlertSeverity
    duration_seconds: int = 0  # Must be true for N seconds
    enabled: bool = True
    webhook_urls: List[str] = field(default_factory=list)
    cooldown_seconds: int = 300
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """A triggered alert"""
    id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    triggered_at: str
    resolved_at: Optional[str] = None
    webhook_sent: bool = False
    webhook_response: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertStats:
    """Alert manager statistics"""
    total_rules: int = 0
    total_alerts: int = 0
    firing_alerts: int = 0
    webhooks_sent: int = 0
    webhooks_failed: int = 0
    last_alert_time: Optional[str] = None


class AlertManager:
    """
    Manages alert rules and triggers webhooks based on metric thresholds.
    """

    def __init__(self, storage_path: str = "swarm/observability/alerts"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.stats = AlertStats()

        # Track condition start time per rule
        self._condition_start: Dict[str, float] = {}
        # Track last fired time per rule (for cooldown)
        self._last_fired: Dict[str, float] = {}

        # Default rules
        self._init_default_rules()

    def _init_default_rules(self) -> None:
        """Create default alert rules"""
        defaults = [
            AlertRule(
                id="high_error_rate",
                name="High Error Rate",
                description="Error rate exceeds 10%",
                metric_name="swarm_tasks_failed",
                condition="gt",
                threshold=10.0,
                severity=AlertSeverity.WARNING,
                duration_seconds=60
            ),
            AlertRule(
                id="constitutional_violation",
                name="Constitutional Violation",
                description="Constitutional guard detected violation",
                metric_name="swarm_constitutional_violations",
                condition="gt",
                threshold=0,
                severity=AlertSeverity.CRITICAL,
                duration_seconds=0
            ),
            AlertRule(
                id="high_queue_depth",
                name="High Queue Depth",
                description="Task queue depth exceeds 100",
                metric_name="swarm_queue_depth",
                condition="gt",
                threshold=100.0,
                severity=AlertSeverity.WARNING,
                duration_seconds=120
            ),
            AlertRule(
                id="circuit_open",
                name="Circuit Breaker Open",
                description="Model circuit breaker has opened",
                metric_name="swarm_circuit_open",
                condition="gt",
                threshold=0,
                severity=AlertSeverity.EMERGENCY,
                duration_seconds=0
            ),
        ]
        for rule in defaults:
            self.rules[rule.id] = rule
        self.stats.total_rules = len(self.rules)

    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule"""
        with self._lock:
            self.rules[rule.id] = rule
            self.stats.total_rules = len(self.rules)
            logger.info(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule"""
        with self._lock:
            if rule_id in self.rules:
                del self.rules[rule_id]
                self.stats.total_rules = len(self.rules)
                return True
            return False

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get an alert rule"""
        with self._lock:
            return self.rules.get(rule_id)

    def list_rules(self) -> List[AlertRule]:
        """List all rules"""
        with self._lock:
            return list(self.rules.values())

    def evaluate(self, metric_name: str, metric_value: float) -> List[Alert]:
        """Evaluate all rules against a metric value. Returns triggered alerts."""
        triggered = []
        with self._lock:
            for rule in self.rules.values():
                if not rule.enabled:
                    continue
                if rule.metric_name != metric_name:
                    continue

                condition_met = self._check_condition(metric_value, rule)

                if condition_met:
                    # For instant alerts (duration_seconds=0), fire immediately
                    if rule.duration_seconds == 0:
                        # Check cooldown
                        last_fired = self._last_fired.get(rule.id, 0)
                        if time.monotonic() - last_fired >= rule.cooldown_seconds:
                            alert = self._fire_alert(rule, metric_value)
                            if alert:
                                triggered.append(alert)
                                self._last_fired[rule.id] = time.monotonic()
                        continue

                    # Track when condition started for duration-based alerts
                    if rule.id not in self._condition_start:
                        self._condition_start[rule.id] = time.monotonic()
                        continue

                    elapsed = time.monotonic() - self._condition_start[rule.id]
                    if elapsed < rule.duration_seconds:
                        continue

                    # Check cooldown
                    last_fired = self._last_fired.get(rule.id, 0)
                    if time.monotonic() - last_fired < rule.cooldown_seconds:
                        continue

                    # Fire alert
                    alert = self._fire_alert(rule, metric_value)
                    if alert:
                        triggered.append(alert)
                        self._last_fired[rule.id] = time.monotonic()
                else:
                    # Reset condition tracking
                    self._condition_start.pop(rule.id, None)
                    # Auto-resolve active alerts
                    self._try_resolve(rule.id, metric_value)

        return triggered

    def _check_condition(self, value: float, rule: AlertRule) -> bool:
        """Check if condition is met"""
        if rule.condition == "gt":
            return value > rule.threshold
        elif rule.condition == "lt":
            return value < rule.threshold
        elif rule.condition == "eq":
            return value == rule.threshold
        elif rule.condition == "ne":
            return value != rule.threshold
        elif rule.condition == "gte":
            return value >= rule.threshold
        elif rule.condition == "lte":
            return value <= rule.threshold
        return False

    def _fire_alert(self, rule: AlertRule, value: float) -> Optional[Alert]:
        """Create and send an alert"""
        import uuid
        alert_id = f"alert-{uuid.uuid4().hex[:8]}"
        alert = Alert(
            id=alert_id,
            rule_id=rule.id,
            rule_name=rule.name,
            severity=rule.severity,
            status=AlertStatus.FIRING,
            message=f"{rule.name}: {rule.metric_name}={value} (threshold: {rule.condition} {rule.threshold})",
            metric_name=rule.metric_name,
            metric_value=value,
            threshold=rule.threshold,
            triggered_at=datetime.now().isoformat(),
            metadata={"description": rule.description, "labels": rule.labels}
        )

        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        self.stats.total_alerts += 1
        self.stats.firing_alerts = sum(
            1 for a in self.active_alerts.values()
            if a.status == AlertStatus.FIRING
        )
        self.stats.last_alert_time = alert.triggered_at

        # Send webhooks
        if rule.webhook_urls:
            self._send_webhooks(alert, rule.webhook_urls)

        logger.warning(f"Alert fired: {alert.message}")
        return alert

    def _try_resolve(self, rule_id: str, value: float) -> None:
        """Auto-resolve active alerts for a rule when condition no longer met"""
        for alert in list(self.active_alerts.values()):
            if alert.rule_id == rule_id and alert.status == AlertStatus.FIRING:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now().isoformat()
                self.active_alerts.pop(alert.id, None)
                self.stats.firing_alerts = sum(
                    1 for a in self.active_alerts.values()
                    if a.status == AlertStatus.FIRING
                )
                logger.info(f"Alert resolved: {alert.message}")

    def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an alert"""
        with self._lock:
            if alert_id not in self.active_alerts:
                return False
            alert = self.active_alerts.pop(alert_id)
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now().isoformat()
            self.stats.firing_alerts = sum(
                1 for a in self.active_alerts.values()
                if a.status == AlertStatus.FIRING
            )
            return True

    def silence_alert(self, alert_id: str, duration_seconds: int = 3600) -> bool:
        """Silence an alert for a duration"""
        with self._lock:
            if alert_id not in self.active_alerts:
                return False
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.SILENCED
            alert.metadata["silenced_until"] = (
                datetime.now() + timedelta(seconds=duration_seconds)
            ).isoformat()
            self.stats.firing_alerts = sum(
                1 for a in self.active_alerts.values()
                if a.status == AlertStatus.FIRING
            )
            return True

    def _send_webhooks(self, alert: Alert, urls: List[str]) -> None:
        """Send webhook notifications"""
        payload = {
            "alert_id": alert.id,
            "rule_id": alert.rule_id,
            "rule_name": alert.rule_name,
            "severity": alert.severity.value,
            "message": alert.message,
            "metric_name": alert.metric_name,
            "metric_value": alert.metric_value,
            "threshold": alert.threshold,
            "triggered_at": alert.triggered_at
        }
        payload_json = json.dumps(payload)

        for url in urls:
            try:
                req = urllib.request.Request(
                    url,
                    data=payload_json.encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    alert.webhook_sent = True
                    alert.webhook_response = response.read().decode("utf-8")[:500]
                    self.stats.webhooks_sent += 1
                    logger.info(f"Webhook sent to {url}")
            except Exception as e:
                logger.error(f"Webhook failed for {url}: {e}")
                self.stats.webhooks_failed += 1

    def get_active_alerts(self) -> List[Alert]:
        """Get all active (firing) alerts"""
        with self._lock:
            return [a for a in self.active_alerts.values() if a.status == AlertStatus.FIRING]

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        with self._lock:
            return self.alert_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get alert manager statistics"""
        with self._lock:
            return {
                "total_rules": self.stats.total_rules,
                "total_alerts": self.stats.total_alerts,
                "firing_alerts": self.stats.firing_alerts,
                "webhooks_sent": self.stats.webhooks_sent,
                "webhooks_failed": self.stats.webhooks_failed,
                "last_alert_time": self.stats.last_alert_time
            }


# Module-level singleton
_default_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create the default alert manager"""
    global _default_manager
    if _default_manager is None:
        _default_manager = AlertManager()
    return _default_manager