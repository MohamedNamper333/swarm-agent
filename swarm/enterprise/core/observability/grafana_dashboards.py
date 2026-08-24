"""
Grafana Dashboard Templates - Production-ready dashboards for Swarm.
"""

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class GrafanaDashboard:
    """Grafana dashboard definition."""
    title: str
    uid: str
    tags: List[str] = field(default_factory=list)
    timezone: str = "utc"
    panels: List[Dict[str, Any]] = field(default_factory=list)
    templating: Dict[str, Any] = field(default_factory=dict)
    time: Dict[str, Any] = field(default_factory=lambda: {
        "from": "now-1h",
        "to": "now"
    })
    refresh: str = "10s"
    version: int = 1
    schema_version: int = 30
    
    def to_json(self) -> str:
        """Convert to Grafana JSON format."""
        return json.dumps({
            "title": self.title,
            "uid": self.uid,
            "tags": self.tags,
            "timezone": self.timezone,
            "panels": self.panels,
            "templating": self.templating,
            "time": self.time,
            "refresh": self.refresh,
            "version": self.version,
            "schemaVersion": self.schema_version,
        }, indent=2)


# =============================================================================
# Standard Panel Templates
# =============================================================================

def create_stat_panel(
    title: str,
    metric: str,
    legend: str = "{{job}}",
    thresholds: List[Dict[str, Any]] = None,
    grid_pos: Dict[str, int] = None,
) -> Dict[str, Any]:
    """Create a stat panel."""
    return {
        "type": "stat",
        "title": title,
        "gridPos": grid_pos or {"x": 0, "y": 0, "w": 6, "h": 4},
        "targets": [{
            "expr": metric,
            "legendFormat": legend,
            "refId": "A",
        }],
        "fieldConfig": {
            "defaults": {
                "thresholds": {
                    "mode": "absolute",
                    "steps": thresholds or [
                        {"color": "green", "value": None},
                        {"color": "yellow", "value": 80},
                        {"color": "red", "value": 95},
                    ],
                },
                "unit": "short",
            },
        },
    }


def create_timeseries_panel(
    title: str,
    metric: str,
    legend: str = "{{job}}",
    unit: str = "short",
    grid_pos: Dict[str, int] = None,
) -> Dict[str, Any]:
    """Create a time series panel."""
    return {
        "type": "timeseries",
        "title": title,
        "gridPos": grid_pos or {"x": 0, "y": 0, "w": 12, "h": 8},
        "targets": [{
            "expr": metric,
            "legendFormat": legend,
            "refId": "A",
        }],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "custom": {
                    "lineWidth": 1,
                    "fillOpacity": 10,
                },
            },
        },
    }


def create_heatmap_panel(
    title: str,
    metric: str,
    legend: str = "{{le}}",
    unit: str = "short",
    grid_pos: Dict[str, int] = None,
) -> Dict[str, Any]:
    """Create a heatmap panel."""
    return {
        "type": "heatmap",
        "title": title,
        "gridPos": grid_pos or {"x": 0, "y": 0, "w": 12, "h": 8},
        "targets": [{
            "expr": metric,
            "legendFormat": legend,
            "format": "heatmap",
            "refId": "A",
        }],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
            },
        },
    }


def create_table_panel(
    title: str,
    metric: str,
    columns: List[str] = None,
    grid_pos: Dict[str, int] = None,
) -> Dict[str, Any]:
    """Create a table panel."""
    return {
        "type": "table",
        "title": title,
        "gridPos": grid_pos or {"x": 0, "y": 0, "w": 24, "h": 10},
        "targets": [{
            "expr": metric,
            "format": "table",
            "refId": "A",
        }],
        "fieldConfig": {
            "defaults": {
                "custom": {
                    "align": "auto",
                },
            },
        },
    }


# =============================================================================
# Swarm System Overview Dashboard
# =============================================================================

def create_swarm_overview_dashboard() -> GrafanaDashboard:
    """Create the main Swarm system overview dashboard."""
    panels = [
        # Row 1: Key Stats
        create_stat_panel(
            title="Active Tenants",
            metric="swarm_tenants_active",
            thresholds=[{"color": "green", "value": None}, {"color": "yellow", "value": 100}, {"color": "red", "value": 500}],
            grid_pos={"x": 0, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="Active Executions",
            metric="swarm_executions_active",
            thresholds=[{"color": "green", "value": None}, {"color": "yellow", "value": 50}, {"color": "red", "value": 200}],
            grid_pos={"x": 6, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="Execution Success Rate",
            metric="swarm_executions_success_rate",
            thresholds=[{"color": "green", "value": 0.99}, {"color": "yellow", "value": 0.95}, {"color": "red", "value": 0.9}],
            grid_pos={"x": 12, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="Avg Execution Time (ms)",
            metric="swarm_executions_avg_duration_ms",
            thresholds=[{"color": "green", "value": None}, {"color": "yellow", "value": 5000}, {"color": "red", "value": 30000}],
            grid_pos={"x": 18, "y": 0, "w": 6, "h": 4},
        ),
        
        # Row 2: Execution Trends
        create_timeseries_panel(
            title="Executions per Minute",
            metric="rate(swarm_executions_total[5m])",
            legend="Status: {{status}}",
            grid_pos={"x": 0, "y": 4, "w": 12, "h": 8},
        ),
        create_timeseries_panel(
            title="Execution Duration (p50, p95, p99)",
            metric="histogram_quantile(0.5, rate(swarm_executions_duration_bucket[5m]))",
            legend="p50",
            grid_pos={"x": 12, "y": 4, "w": 12, "h": 8},
        ),
        
        # Row 3: Resource Usage
        create_timeseries_panel(
            title="Memory Usage by Sandbox",
            metric="swarm_sandbox_memory_bytes",
            legend="Sandbox: {{sandbox_id}}",
            unit="bytes",
            grid_pos={"x": 0, "y": 12, "w": 12, "h": 8},
        ),
        create_timeseries_panel(
            title="CPU Usage by Sandbox",
            metric="swarm_sandbox_cpu_seconds_total",
            legend="Sandbox: {{sandbox_id}}",
            unit="seconds",
            grid_pos={"x": 12, "y": 12, "w": 12, "h": 8},
        ),
        
        # Row 4: Error Rates
        create_timeseries_panel(
            title="Error Rate by Type",
            metric="rate(swarm_executions_errors_total[5m])",
            legend="Error: {{error_type}}",
            grid_pos={"x": 0, "y": 20, "w": 12, "h": 8},
        ),
        create_timeseries_panel(
            title="Timeout / OOM / Killed Rates",
            metric="rate(swarm_executions_status_total{status=~\"timeout|oom|killed\"}[5m])",
            legend="Status: {{status}}",
            grid_pos={"x": 12, "y": 20, "w": 12, "h": 8},
        ),
    ]
    
    return GrafanaDashboard(
        title="Swarm System Overview",
        uid="swarm-overview",
        tags=["swarm", "overview", "system"],
        panels=panels,
        templating={
            "list": [
                {
                    "name": "tenant",
                    "type": "query",
                    "datasource": "Prometheus",
                    "query": "label_values(swarm_tenants_active, tenant_id)",
                    "refresh": 1,
                    "includeAll": True,
                    "multi": True,
                },
                {
                    "name": "sandbox",
                    "type": "query",
                    "datasource": "Prometheus",
                    "query": "label_values(swarm_sandbox_memory_bytes, sandbox_id)",
                    "refresh": 1,
                    "includeAll": True,
                    "multi": True,
                },
            ]
        },
    )


# =============================================================================
# Sandbox Execution Details Dashboard
# =============================================================================

def create_sandbox_dashboard() -> GrafanaDashboard:
    """Create sandbox execution details dashboard."""
    panels = [
        create_stat_panel(
            title="Active Sandboxes",
            metric="swarm_sandboxes_active",
            grid_pos={"x": 0, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="Sandbox Queue Depth",
            metric="swarm_sandbox_queue_depth",
            grid_pos={"x": 6, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="Cold Start Rate",
            metric="rate(swarm_sandbox_cold_starts_total[5m])",
            grid_pos={"x": 12, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="Avg Cold Start Time (ms)",
            metric="swarm_sandbox_cold_start_duration_ms",
            grid_pos={"x": 18, "y": 0, "w": 6, "h": 4},
        ),
        
        create_timeseries_panel(
            title="Sandbox Lifecycle",
            metric="rate(swarm_sandbox_events_total[5m])",
            legend="Event: {{event}}",
            grid_pos={"x": 0, "y": 4, "w": 12, "h": 8},
        ),
        create_timeseries_panel(
            title="Resource Limits Utilization",
            metric="swarm_sandbox_resource_utilization_ratio",
            legend="Resource: {{resource}}, Sandbox: {{sandbox_id}}",
            grid_pos={"x": 12, "y": 4, "w": 12, "h": 8},
        ),
        
        create_heatmap_panel(
            title="Execution Duration Distribution",
            metric="rate(swarm_executions_duration_bucket[5m])",
            unit="ms",
            grid_pos={"x": 0, "y": 12, "w": 12, "h": 8},
        ),
        create_table_panel(
            title="Top Slow Executions",
            metric="topk(20, swarm_executions_duration_ms)",
            columns=["execution_id", "tenant_id", "language", "duration_ms"],
            grid_pos={"x": 12, "y": 12, "w": 12, "h": 10},
        ),
    ]
    
    return GrafanaDashboard(
        title="Swarm Sandbox Execution Details",
        uid="swarm-sandbox",
        tags=["swarm", "sandbox", "execution"],
        panels=panels,
        templating={
            "list": [
                {
                    "name": "tenant",
                    "type": "query",
                    "datasource": "Prometheus",
                    "query": "label_values(swarm_sandboxes_active, tenant_id)",
                    "includeAll": True,
                    "multi": True,
                },
            ]
        },
    )


# =============================================================================
# Authentication & Security Dashboard
# =============================================================================

def create_auth_security_dashboard() -> GrafanaDashboard:
    """Create authentication and security dashboard."""
    panels = [
        create_stat_panel(
            title="Active Sessions",
            metric="swarm_auth_sessions_active",
            grid_pos={"x": 0, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="Failed Login Rate",
            metric="rate(swarm_auth_login_failures_total[5m])",
            thresholds=[{"color": "green", "value": None}, {"color": "yellow", "value": 10}, {"color": "red", "value": 50}],
            grid_pos={"x": 6, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="MFA Enabled Users %",
            metric="swarm_users_mfa_enabled_ratio",
            thresholds=[{"color": "green", "value": 0.8}, {"color": "yellow", "value": 0.5}, {"color": "red", "value": 0.2}],
            grid_pos={"x": 12, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="Active Alerts",
            metric="swarm_alerts_active",
            thresholds=[{"color": "green", "value": 0}, {"color": "yellow", "value": 5}, {"color": "red", "value": 20}],
            grid_pos={"x": 18, "y": 0, "w": 6, "h": 4},
        ),
        
        create_timeseries_panel(
            title="Login Attempts (Success vs Failure)",
            metric="rate(swarm_auth_login_total[5m])",
            legend="Result: {{result}}",
            grid_pos={"x": 0, "y": 4, "w": 12, "h": 8},
        ),
        create_timeseries_panel(
            title="Token Operations",
            metric="rate(swarm_tokens_operations_total[5m])",
            legend="Operation: {{operation}}",
            grid_pos={"x": 12, "y": 4, "w": 12, "h": 8},
        ),
        
        create_heatmap_panel(
            title="Auth Latency Distribution",
            metric="rate(swarm_auth_latency_seconds_bucket[5m])",
            unit="s",
            grid_pos={"x": 0, "y": 12, "w": 12, "h": 8},
        ),
        create_table_panel(
            title="Recent Security Events",
            metric="swarm_security_events",
            columns=["timestamp", "event_type", "severity", "user_id", "details"],
            grid_pos={"x": 12, "y": 12, "w": 12, "h": 10},
        ),
    ]
    
    return GrafanaDashboard(
        title="Swarm Authentication & Security",
        uid="swarm-auth-security",
        tags=["swarm", "auth", "security"],
        panels=panels,
    )


# =============================================================================
# Multi-Tenancy Dashboard
# =============================================================================

def create_multitenant_dashboard() -> GrafanaDashboard:
    """Create multi-tenancy dashboard."""
    panels = [
        create_stat_panel(
            title="Total Tenants",
            metric="swarm_tenants_total",
            grid_pos={"x": 0, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="Active Tenants",
            metric="swarm_tenants_active",
            grid_pos={"x": 6, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="Quota Utilization (Avg)",
            metric="avg(swarm_tenant_quota_utilization)",
            thresholds=[{"color": "green", "value": None}, {"color": "yellow", "value": 0.7}, {"color": "red", "value": 0.9}],
            grid_pos={"x": 12, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="Cross-Tenant Isolation Violations",
            metric="swarm_cross_tenant_violations_total",
            thresholds=[{"color": "green", "value": 0}, {"color": "red", "value": 1}],
            grid_pos={"x": 18, "y": 0, "w": 6, "h": 4},
        ),
        
        create_timeseries_panel(
            title="Tenant Activity",
            metric="rate(swarm_tenant_requests_total[5m])",
            legend="Tenant: {{tenant_id}}",
            grid_pos={"x": 0, "y": 4, "w": 12, "h": 8},
        ),
        create_timeseries_panel(
            title="Resource Usage by Tenant",
            metric="swarm_tenant_resource_usage",
            legend="Tenant: {{tenant_id}}, Resource: {{resource}}",
            grid_pos={"x": 12, "y": 4, "w": 12, "h": 8},
        ),
        
        create_table_panel(
            title="Tenant Quota Status",
            metric="swarm_tenant_quota_status",
            columns=["tenant_id", "resource", "used", "limit", "utilization_percent"],
            grid_pos={"x": 0, "y": 12, "w": 24, "h": 10},
        ),
    ]
    
    return GrafanaDashboard(
        title="Swarm Multi-Tenancy",
        uid="swarm-multitenant",
        tags=["swarm", "multitenant", "tenants"],
        panels=panels,
    )


# =============================================================================
# Infrastructure & Runtime Dashboard
# =============================================================================

def create_infrastructure_dashboard() -> GrafanaDashboard:
    """Create infrastructure and runtime dashboard."""
    panels = [
        create_stat_panel(
            title="CPU Usage",
            metric="process_cpu_seconds_total",
            thresholds=[{"color": "green", "value": None}, {"color": "yellow", "value": 0.7}, {"color": "red", "value": 0.9}],
            grid_pos={"x": 0, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="Memory Usage",
            metric="process_resident_memory_bytes / process_virtual_memory_bytes",
            thresholds=[{"color": "green", "value": None}, {"color": "yellow", "value": 0.8}, {"color": "red", "value": 0.95}],
            grid_pos={"x": 6, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="Goroutines / Threads",
            metric="go_goroutines",
            grid_pos={"x": 12, "y": 0, "w": 6, "h": 4},
        ),
        create_stat_panel(
            title="GC Pause (p99)",
            metric="go_gc_duration_seconds{pquantile=\"0.99\"}",
            grid_pos={"x": 18, "y": 0, "w": 6, "h": 4},
        ),
        
        create_timeseries_panel(
            title="Request Rate",
            metric="rate(http_requests_total[5m])",
            legend="Method: {{method}}, Path: {{path}}",
            grid_pos={"x": 0, "y": 4, "w": 12, "h": 8},
        ),
        create_timeseries_panel(
            title="Request Latency (p50, p95, p99)",
            metric="histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))",
            legend="Quantile: {{quantile}}",
            grid_pos={"x": 12, "y": 4, "w": 12, "h": 8},
        ),
        
        create_timeseries_panel(
            title="Database Connections",
            metric="db_connections_active",
            legend="Pool: {{pool}}",
            grid_pos={"x": 0, "y": 12, "w": 12, "h": 8},
        ),
        create_timeseries_panel(
            title="Cache Hit Ratio",
            metric="rate(cache_hits_total[5m]) / rate(cache_requests_total[5m])",
            grid_pos={"x": 12, "y": 12, "w": 12, "h": 8},
        ),
    ]
    
    return GrafanaDashboard(
        title="Swarm Infrastructure & Runtime",
        uid="swarm-infrastructure",
        tags=["swarm", "infrastructure", "runtime"],
        panels=panels,
    )


# =============================================================================
# All Dashboards Registry
# =============================================================================

DASHBOARDS = {
    "overview": create_swarm_overview_dashboard(),
    "sandbox": create_sandbox_dashboard(),
    "auth_security": create_auth_security_dashboard(),
    "multitenant": create_multitenant_dashboard(),
    "infrastructure": create_infrastructure_dashboard(),
}


def get_dashboard(name: str) -> Optional[GrafanaDashboard]:
    """Get a dashboard by name."""
    return DASHBOARDS.get(name)


def list_dashboards() -> List[str]:
    """List available dashboards."""
    return list(DASHBOARDS.keys())


def export_all_dashboards(output_dir: str) -> None:
    """Export all dashboards to JSON files."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    for name, dashboard in DASHBOARDS.items():
        filepath = os.path.join(output_dir, f"{name}.json")
        with open(filepath, "w") as f:
            f.write(dashboard.to_json())
        print(f"Exported: {filepath}")


def import_dashboard(filepath: str) -> GrafanaDashboard:
    """Import dashboard from JSON file."""
    with open(filepath, "r") as f:
        data = json.load(f)
    
    dashboard = GrafanaDashboard(
        title=data.get("title", ""),
        uid=data.get("uid", ""),
        tags=data.get("tags", []),
        panels=data.get("panels", []),
        templating=data.get("templating", {}),
    )
    return dashboard
