"""
Deployment - Blue/Green, Canary, and Disaster Recovery orchestration.
"""

from .blue_green import (
    DeploymentStatus,
    Environment,
    DeploymentTarget,
    DeploymentPlan,
    DeploymentStep,
    DeploymentProvider,
    KubernetesDeploymentProvider,
    BlueGreenDeploymentManager,
    CanaryDeploymentManager,
    create_deployment_provider,
    create_blue_green_manager,
    create_canary_manager,
)

from .disaster_recovery import (
    BackupStatus,
    RestoreStatus,
    FailoverStatus,
    RecoveryTier,
    BackupTarget,
    BackupJob,
    RestoreJob,
    FailoverPlan,
    DrillResult,
    BackupProvider,
    FilesystemBackupProvider,
    DatabaseBackupProvider,
    BackupManager,
    FailoverManager,
    DisasterRecoveryCoordinator,
    create_backup_manager,
    create_failover_manager,
    create_dr_coordinator,
)

__all__ = [
    # Blue/Green
    "DeploymentStatus",
    "Environment",
    "DeploymentTarget",
    "DeploymentPlan",
    "DeploymentStep",
    "DeploymentProvider",
    "KubernetesDeploymentProvider",
    "BlueGreenDeploymentManager",
    "CanaryDeploymentManager",
    "create_deployment_provider",
    "create_blue_green_manager",
    "create_canary_manager",
    # Disaster Recovery
    "BackupStatus",
    "RestoreStatus",
    "FailoverStatus",
    "RecoveryTier",
    "BackupTarget",
    "BackupJob",
    "RestoreJob",
    "FailoverPlan",
    "DrillResult",
    "BackupProvider",
    "FilesystemBackupProvider",
    "DatabaseBackupProvider",
    "BackupManager",
    "FailoverManager",
    "DisasterRecoveryCoordinator",
    "create_backup_manager",
    "create_failover_manager",
    "create_dr_coordinator",
]
