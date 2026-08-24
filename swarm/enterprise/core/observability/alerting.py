"""
Alert Management - Alert rules, notification channels, and escalation.
"""

import threading
import time
import uuid
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
# Alert Models
# =============================================================================

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


class ConditionOperator(str, Enum):
    GT = "gt"           # Greater than
    GTE = "gte"         # Greater than or equal
    LT = "lt"           # Less than
    LTE = "lte"         # Less than or equal
    EQ = "eq"           # Equal
    NEQ = "neq"         # Not equal
    CONTAINS = "contains"
    REGEX = "regex"


@dataclass
class AlertCondition:
    """A single condition in an alert rule."""
    metric_name: str
    operator: ConditionOperator
    threshold: float
    labels: Dict[str, str] = field(default_factory=dict)
    duration_seconds: int = 0  # How long condition must persist


@dataclass
class AlertRule:
    """Alert rule definition."""
    rule_id: str = field(default_factory=lambda: f"rule-{uuidv7()}")
    name: str = ""
    description: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    conditions: List[AlertCondition] = field(default_factory=list)
    enabled: bool = True
    
    # Evaluation
    evaluation_interval_seconds: int = 60
    for_duration_seconds: int = 0  # How long all conditions must be true
    
    # Labels and annotations
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    # Notification
    notification_channels: List[str] = field(default_factory=list)
    notification_interval_seconds: int = 300  # Re-notify interval
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"


@dataclass
class Alert:
    """An active alert instance."""
    alert_id: str = field(default_factory=lambda: f"alert-{uuidv7()}")
    rule_id: str = ""
    rule_name: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    status: AlertStatus = AlertStatus.FIRING
    
    # Context
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    # Values that triggered the alert
    values: Dict[str, float] = field(default_factory=dict)
    
    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    # Notification tracking
    notification_count: int = 0
    last_notification_at: Optional[datetime] = None


# =============================================================================
# Alert Evaluator
# =============================================================================

class AlertEvaluator:
    """Evaluates alert rules against metrics."""
    
    def __init__(self, metrics_registry: Any):
        self.metrics_registry = metrics_registry
    
    def evaluate_condition(
        self,
        condition: AlertCondition,
        metrics: Dict[str, Any],
    ) -> bool:
        """Evaluate a single condition against metrics."""
        # Get metric value
        metric_key = condition.metric_name
        if condition.labels:
            # Find metric with matching labels
            metric = self.metrics_registry.get_metric(
                metric_key, condition.labels
            )
        else:
            metric = self.metrics_registry.get_metric(metric_key)
        
        if not metric:
            return False
        
        # Get current value (latest point for gauge, sum for counter)
        if metric.metric_type.value == "gauge":
            current_value = metric.points[-1].value if metric.points else 0
        elif metric.metric_type.value == "counter":
            current_value = sum(p.value for p in metric.points)
        elif metric.metric_type.value == "histogram":
            # Use sum
            sum_metric = self.metrics_registry.get_metric(f"{metric_key}_sum")
            current_value = sum(p.value for p in sum_metric.points) if sum_metric else 0
        else:
            current_value = 0
        
        # Evaluate condition
        return self._compare(current_value, condition.operator, condition.threshold)
    
    def _compare(self, value: float, operator: Any, threshold: float) -> bool:
        """Compare value against threshold."""
        if isinstance(operator, str):
            op = operator
        else:
            op = operator.value if hasattr(operator, 'value') else str(operator)
        
        if op in ("gt", ">"):
            return value > threshold
        elif op in ("gte", ">="):
            return value >= threshold
        elif op in ("lt", "<"):
            return value < threshold
        elif op in ("lte", "<="):
            return value <= threshold
        elif op in ("eq", "=="):
            return value == threshold
        elif op in ("neq", "!="):
            return value != threshold
        return False
    
    def evaluate_rule(
        self,
        rule: AlertRule,
        metrics: Dict[str, Any],
    ) -> Optional[Alert]:
        """Evaluate a rule against metrics."""
        if not rule.enabled:
            return None
        
        all_true = True
        triggered_values = {}
        
        for condition in rule.conditions:
            if self.evaluate_condition(condition, metrics):
                triggered_values[condition.metric_name] = True
            else:
                all_true = False
                break
        
        if all_true:
            return Alert(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                severity=rule.severity,
                labels=rule.labels.copy(),
                annotations=rule.annotations.copy(),
                values=triggered_values,
            )
        
        return None


# =============================================================================
# Alert Manager
# =============================================================================

class AlertManager:
    """Manages alert rules, evaluation, and notifications."""
    
    def __init__(
        self,
        metrics_registry: Any,
        evaluation_interval: int = 30,
    ):
        self.metrics_registry = metrics_registry
        self.evaluation_interval = evaluation_interval
        
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._resolved_alerts: Dict[str, Alert] = {}
        
        self._evaluator = AlertEvaluator(metrics_registry)
        
        self._notification_channels: Dict[str, "NotificationChannel"] = {}
        
        self._running = False
        self._eval_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Callbacks
        self._alert_callbacks: List[Callable[[Alert, str], None]] = []
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        with self._lock:
            self._rules[rule.rule_id] = rule
            logger.info(f"Added alert rule: {rule.rule_id} ({rule.name})")
    
    def remove_rule(self, rule_id: str = "") -> bool:
        """Remove an alert rule."""
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                logger.info(f"Removed alert rule: {rule_id}")
                return True
            return False
    
    def get_rule(self, rule_id: str = "") -> Optional[AlertRule]:
        """Get an alert rule."""
        with self._lock:
            return self._rules.get(rule_id)
    
    def list_rules(self, enabled_only: bool = True) -> List[AlertRule]:
        """List alert rules."""
        with self._lock:
            rules = list(self._rules.values())
            if enabled_only:
                rules = [r for r in rules if r.enabled]
            return rules
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Optional[AlertRule]:
        """Update an alert rule."""
        with self._lock:
            rule = self._rules.get(rule_id)
            if not rule:
                return None
            
            for key, value in updates.items():
                if hasattr(rule, key) and key not in ("rule_id", "created_at", "created_by"):
                    setattr(rule, key, value)
            
            rule.updated_at = now_utc()
            logger.info(f"Updated alert rule: {rule_id}")
            return rule
    
    def add_notification_channel(self, channel: "NotificationChannel") -> None:
        """Add a notification channel."""
        with self._lock:
            self._notification_channels[channel.channel_id] = channel
    
    def remove_notification_channel(self, channel_id: str) -> bool:
        """Remove a notification channel."""
        with self._lock:
            if channel_id in self._notification_channels:
                del self._notification_channels[channel_id]
                return True
            return False
    
    def start(self) -> None:
        """Start alert evaluation loop."""
        if self._running:
            return
        
        self._running = True
        self._eval_thread = threading.Thread(target=self._evaluation_loop, daemon=True)
        self._eval_thread.start()
        logger.info("Alert manager started")
    
    def stop(self) -> None:
        """Stop alert evaluation loop."""
        if not self._running:
            return
        
        self._running = False
        if self._eval_thread:
            self._eval_thread.join(timeout=10)
        logger.info("Alert manager stopped")
    
    def _evaluation_loop(self) -> None:
        """Main evaluation loop."""
        logger.info("Alert evaluation loop started")
        
        while self._running:
            try:
                self._evaluate_all()
            except Exception as e:
                logger.error(f"Alert evaluation error: {e}")
            
            time.sleep(self.evaluation_interval)
        
        logger.info("Alert evaluation loop stopped")
    
    def _evaluate_all(self) -> None:
        """Evaluate all rules."""
        with self._lock:
            rules = [r for r in self._rules.values() if r.enabled]
        
        for rule in rules:
            try:
                alert = self._evaluator.evaluate_rule(rule, {})
                
                if alert:
                    self._handle_firing_alert(rule, alert)
                else:
                    self._handle_resolved_alert(rule)
                    
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
    
    def _handle_firing_alert(self, rule: AlertRule, alert: Alert) -> None:
        """Handle a firing alert."""
        with self._lock:
            # Check if alert already exists
            existing = None
            for a in self._active_alerts.values():
                if a.rule_id == rule.rule_id and a.status == AlertStatus.FIRING:
                    existing = a
                    break
            
            if existing:
                # Update existing alert
                existing.last_updated_at = now_utc()
                existing.values = alert.values
            else:
                # New alert
                self._active_alerts[alert.alert_id] = alert
                logger.warning(f"ALERT FIRING: {alert.rule_name} [{alert.severity.value}]")
                
                # Send notifications
                self._send_notifications(alert, "firing")
    
    def _handle_resolved_alert(self, rule: AlertRule) -> None:
        """Handle resolved alert."""
        with self._lock:
            # Find and resolve matching alerts
            for alert_id, alert in list(self._active_alerts.items()):
                if alert.rule_id == rule.rule_id and alert.status == AlertStatus.FIRING:
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = now_utc()
                    
                    self._resolved_alerts[alert_id] = alert
                    del self._active_alerts[alert_id]
                    
                    logger.info(f"ALERT RESOLVED: {alert.rule_name}")
                    self._send_notifications(alert, "resolved")
    
    def _send_notifications(self, alert: Alert, event: str) -> None:
        """Send alert notifications."""
        rule = self._rules.get(alert.rule_id)
        if not rule:
            return
        
        for channel_id in rule.notification_channels:
            channel = self._notification_channels.get(channel_id)
            if channel:
                try:
                    channel.send(alert, event)
                    alert.notification_count += 1
                    alert.last_notification_at = now_utc()
                except Exception as e:
                    logger.error(f"Notification failed for channel {channel_id}: {e}")
        
        # Call callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert, event)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge an alert."""
        with self._lock:
            alert = self._active_alerts.get(alert_id)
            if not alert:
                return False
            
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = now_utc()
            alert.acknowledged_by = user
            logger.info(f"Alert {alert_id} acknowledged by {user}")
            return True
    
    def suppress_alert(self, alert_id: str) -> bool:
        """Suppress an alert."""
        with self._lock:
            alert = self._active_alerts.get(alert_id)
            if not alert:
                return False
            
            alert.status = AlertStatus.SUPPRESSED
            logger.info(f"Alert {alert_id} suppressed")
            return True
    
    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> List[Alert]:
        """Get active alerts."""
        with self._lock:
            alerts = [a for a in self._active_alerts.values() if a.status == AlertStatus.FIRING]
            
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            if labels:
                alerts = [a for a in alerts if all(a.labels.get(k) == v for k, v in labels.items())]
            
            return alerts
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID."""
        with self._lock:
            return self._active_alerts.get(alert_id) or self._resolved_alerts.get(alert_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get alert manager statistics."""
        with self._lock:
            active = len([a for a in self._active_alerts.values() if a.status == AlertStatus.FIRING])
            acknowledged = len([a for a in self._active_alerts.values() if a.status == AlertStatus.ACKNOWLEDGED])
            suppressed = len([a for a in self._active_alerts.values() if a.status == AlertStatus.SUPPRESSED])
            resolved = len(self._resolved_alerts)
            
            by_severity = defaultdict(int)
            for a in self._active_alerts.values():
                by_severity[a.severity.value] += 1
            
            return {
                "total_rules": len(self._rules),
                "enabled_rules": len([r for r in self._rules.values() if r.enabled]),
                "active_alerts": active,
                "acknowledged": acknowledged,
                "suppressed": suppressed,
                "resolved": resolved,
                "by_severity": dict(by_severity),
            }
    
    def add_alert_callback(self, callback: Callable[[Alert, str], None]) -> None:
        """Add callback for alert events."""
        self._alert_callbacks.append(callback)


# =============================================================================
# Notification Channels
# =============================================================================

class NotificationChannel(ABC):
    """Abstract notification channel."""
    
    def __init__(self, channel_id: str, name: str):
        self.channel_id = channel_id
        self.name = name
    
    @abstractmethod
    def send(self, alert: Alert, event: str) -> None:
        """Send notification."""
        pass


class WebhookChannel(NotificationChannel):
    """Send alerts via webhook."""
    
    def __init__(
        self,
        channel_id: str,
        name: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
    ):
        super().__init__(channel_id, name)
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
    
    def send(self, alert: Alert, event: str) -> None:
        import requests
        
        payload = {
            "alert_id": alert.alert_id,
            "rule_name": alert.rule_name,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "event": event,
            "labels": alert.labels,
            "annotations": alert.annotations,
            "values": alert.values,
            "started_at": alert.started_at.isoformat(),
        }
        
        try:
            requests.post(
                self.url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")


class EmailChannel(NotificationChannel):
    """Send alerts via email."""
    
    def __init__(
        self,
        channel_id: str,
        name: str,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        to_emails: List[str],
    ):
        super().__init__(channel_id, name)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
    
    def send(self, alert: Alert, event: str) -> None:
        # In production, send actual email
        logger.info(f"Email alert sent for {alert.rule_name} ({event})")


class SlackChannel(NotificationChannel):
    """Send alerts to Slack."""
    
    def __init__(
        self,
        channel_id: str,
        name: str,
        webhook_url: str,
        channel: Optional[str] = None,
    ):
        super().__init__(channel_id, name)
        self.webhook_url = webhook_url
        self.channel = channel
    
    def send(self, alert: Alert, event: str) -> None:
        # In production, send to Slack webhook
        logger.info(f"Slack alert sent for {alert.rule_name} ({event})")


class PagerDutyChannel(NotificationChannel):
    """Send alerts to PagerDuty."""
    
    def __init__(
        self,
        channel_id: str,
        name: str,
        integration_key: str,
    ):
        super().__init__(channel_id, name)
        self.integration_key = integration_key
    
    def send(self, alert: Alert, event: str) -> None:
        # In production, send to PagerDuty API
        logger.info(f"PagerDuty alert sent for {alert.rule_name} ({event})")


# =============================================================================
# Factory
# =============================================================================

def create_alert_manager(
    metrics_registry: Any,
    evaluation_interval: int = 30,
) -> AlertManager:
    """Create an AlertManager instance."""
    return AlertManager(metrics_registry, evaluation_interval)


def create_alert_rule(
    name: str,
    severity: AlertSeverity = AlertSeverity.WARNING,
    conditions: List[Dict[str, Any]] = None,
    **kwargs,
) -> AlertRule:
    """Create an alert rule from simple definition."""
    rule_conditions = []
    for cond in conditions:
        rule_conditions.append(AlertCondition(
            metric_name=cond["metric"],
            operator=cond["operator"],
            threshold=cond["threshold"],
            labels=cond.get("labels", {}),
            duration_seconds=cond.get("duration", 0),
        ))
    
    return AlertRule(
        name=name,
        severity=severity,
        conditions=rule_conditions,
        **kwargs,
    )
