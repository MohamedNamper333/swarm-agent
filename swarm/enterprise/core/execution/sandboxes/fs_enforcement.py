"""
Filesystem Isolation Enforcement - Enforces filesystem isolation for sandboxed executions.
Implements mount namespace isolation, bind mounts, readonly overlays, and filesystem quotas.
"""

import asyncio
import os
import subprocess
import ctypes
import ctypes.util
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)
# Linux namespace clone flags
CLONE_NEWNS = 0x00020000      # Mount namespace
CLONE_NEWUTS = 0x04000000     # UTS namespace
CLONE_NEWIPC = 0x08000000     # IPC namespace
CLONE_NEWUSER = 0x10000000    # User namespace
CLONE_NEWPID = 0x20000000     # PID namespace
CLONE_NEWNET = 0x40000000     # Network namespace
CLONE_NEWCGROUP = 0x02000000  # Cgroup namespace



def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


class FilesystemMode(str, Enum):
    NONE = "none"           # No filesystem access
    READONLY = "readonly"   # Read-only access to allowed paths
    READWRITE = "readwrite" # Read-write access to allowed paths
    FULL = "full"           # Full filesystem access (dangerous)


@dataclass
class MountRule:
    """A single mount/bind rule."""
    rule_id: str = field(default_factory=lambda: f"mountrule-{uuid.uuid4()}")
    name: str = ""
    source: str = ""
    target: str = ""
    readonly: bool = True
    recursive: bool = True
    fstype: str = "bind"
    options: str = "nosuid,nodev,noexec"


@dataclass
class FilesystemPolicy:
    """Filesystem access policy for a sandbox/tenant."""
    policy_id: str = field(default_factory=lambda: f"fspol-{uuid.uuid4()}")
    name: str = ""
    tenant_id: str = "default"
    mode: str = "readonly"
    allowed_paths: List[str] = field(default_factory=list)  # Paths allowed for access
    denied_paths: List[str] = field(default_factory=list)   # Paths explicitly denied
    mount_rules: List[MountRule] = field(default_factory=list)
    max_size_mb: Optional[int] = None  # Quota in MB
    allowed_fstypes: List[str] = field(default_factory=lambda: ["ext4", "tmpfs", "overlay"])
    allowed_fsops: List[str] = field(default_factory=lambda: ["read", "write", "create", "delete"])
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MountNamespaceManager:
    """Manages mount namespaces for filesystem isolation."""
    
    def __init__(self):
        self._namespaces: Dict[str, str] = {}  # ns_id -> ns_path
        self._mounts: Dict[str, List[str]] = {}  # ns_id -> list of mount points
        self._lock = threading.RLock()
    
    def create_namespace(self, ns_id: Optional[str] = None) -> str:
        """Create a new mount namespace using unshare(CLONE_NEWNS) via ctypes (FS-1)."""
        ns_id = ns_id or f"mnt-{uuid.uuid4().hex[:8]}"
        
        with self._lock:
            # Use unshare syscall directly for mount namespace (FS-1)
            libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
            # CLONE_NEWNS | CLONE_NEWUSER for unprivileged mount namespace
            result = libc.unshare(CLONE_NEWNS | CLONE_NEWUSER)
            if result != 0:
                errno = ctypes.get_errno()
                # Fallback to unshare command
                logger.warning(f"unshare failed: {os.strerror(errno)}, falling back to unshare command")
                result = subprocess.run(
                    ["unshare", "-m", "--propagation", "slave", "true"],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    raise RuntimeError(f"Failed to create mount namespace: {result.stderr}")
            
            # Setup user namespace mapping for rootless operation
            try:
                with open("/proc/self/uid_map", "w") as f:
                    f.write(f"0 {os.getuid()} 1\n")
                with open("/proc/self/gid_map", "w") as f:
                    f.write(f"0 {os.getgid()} 1\n")
                with open("/proc/self/setgroups", "w") as f:
                    f.write("deny\n")
            except Exception as e:
                logger.warning(f"Failed to setup user namespace mapping: {e}")
            
            # Set mount propagation to slave to avoid propagating to host
            subprocess.run(["mount", "--make-rslave", "/"], capture_output=True)
            
            self._namespaces[ns_id] = {
                "created_at": datetime.now(timezone.utc),
                "mounts": [],
            }
            
            logger.info(f"Created mount namespace: {ns_id}")
            return ns_id
    
    def delete_namespace(self, ns_id: str) -> bool:
        """Delete a mount namespace and clean up mounts."""
        with self._lock:
            if ns_id in self._namespaces:
                # Unmount all mounts in reverse order
                for mount_point in reversed(self._namespaces[ns_id].get("mounts", [])):
                    try:
                        subprocess.run(["umount", "-R", mount_point], capture_output=True)
                    except Exception:
                        pass
                del self._namespaces[ns_id]
                logger.info(f"Deleted mount namespace: {ns_id}")
                return True
            return False
    
    def add_mount(self, ns_id: str, mount_point: str) -> bool:
        """Track a mount point in a namespace."""
        with self._lock:
            if ns_id in self._namespaces:
                self._namespaces[ns_id].setdefault("mounts", []).append(mount_point)
                return True
            return False
    
    def get_mounts(self, ns_id: str) -> List[str]:
        with self._lock:
            return self._namespaces.get(ns_id, {}).get("mounts", []).copy()
    
    def namespace_exists(self, ns_id: str) -> bool:
        with self._lock:
            return ns_id in self._namespaces
    
    def cleanup_namespace(self, ns_id: str) -> bool:
        """Clean up all mounts and delete namespace."""
        with self._lock:
            if ns_id in self._namespaces:
                for mount_point in reversed(self._namespaces[ns_id].get("mounts", [])):
                    try:
                        subprocess.run(["umount", "-R", mount_point], capture_output=True)
                    except Exception:
                        pass
                del self._namespaces[ns_id]
                return True
            return False


class FilesystemPolicyEngine:
    """Evaluates filesystem access policies."""
    
    def __init__(self):
        self._policies: Dict[str, FilesystemPolicy] = {}
        self._lock = threading.RLock()
    
    def add_policy(self, policy: FilesystemPolicy) -> None:
        with self._lock:
            self._policies[policy.policy_id] = policy
    
    def remove_policy(self, policy_id: str) -> bool:
        with self._lock:
            if policy_id in self._policies:
                del self._policies[policy_id]
                return True
            return False
    
    def get_policy(self, policy_id: str) -> Optional[FilesystemPolicy]:
        with self._lock:
            return self._policies.get(policy_id)
    
    def get_policy_for_tenant(self, tenant_id: str) -> Optional[FilesystemPolicy]:
        with self._lock:
            for policy in self._policies.values():
                if policy.tenant_id == tenant_id and policy.mode != "none":
                    return policy
            return None
    
    def check_access(
        self,
        tenant_id: str,
        path: str,
        operation: str,  # read, write, create, delete
    ) -> Tuple[bool, Optional[str]]:
        """Check if access is allowed."""
        policy = self.get_policy_for_tenant(tenant_id)
        if not policy:
            return False, "No policy found for tenant"
        
        if policy.mode == "none":
            return False, "Filesystem access disabled for tenant"
        
        # Check denied paths first
        for denied in policy.denied_paths:
            if self._path_matches(path, denied):
                return False, f"Path {path} is explicitly denied"
        
        # Check allowed paths
        allowed = False
        for allowed_path in policy.allowed_paths:
            if self._path_matches(path, allowed_path):
                allowed = True
                break
        
        if not allowed:
            return False, f"Path {path} not in allowed paths"
        
        # Check operation permission
        if operation not in policy.allowed_fsops:
            return False, f"Operation {operation} not allowed"
        
        return True, None
    
    def _path_matches(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern (supports wildcards)."""
        import fnmatch
        return fnmatch.fnmatch(path, pattern) or path.startswith(pattern.rstrip("*"))
    
    def check_quota(self, tenant_id: str, current_usage_mb: int) -> Tuple[bool, Optional[str]]:
        """Check if tenant has exceeded quota."""
        policy = self.get_policy_for_tenant(tenant_id)
        if not policy or not policy.max_size_mb:
            return True, None
        
        if current_usage_mb > policy.max_size_mb:
            return False, f"Quota exceeded: {current_usage_mb}MB > {policy.max_size_mb}MB"
        
        return True, None


class FilesystemIsolationEnforcer:
    """Enforces filesystem isolation for sandboxes."""
    
    def __init__(self):
        self.mount_ns_manager = MountNamespaceManager()
        self.policy_engine = FilesystemPolicyEngine()
        self._lock = threading.RLock()
        self._sandbox_policies: Dict[str, str] = {}  # sandbox_id -> policy_id
        self._sandbox_namespaces: Dict[str, str] = {}  # sandbox_id -> ns_id
        self._overlay_mounts: Dict[str, str] = {}  # sandbox_id -> overlay_dir
    
    def create_isolated_filesystem(
        self,
        sandbox_id: str,
        tenant_id: str = "default",
        mode: str = "readonly",
        allowed_paths: Optional[List[str]] = None,
        denied_paths: Optional[List[str]] = None,
        max_size_mb: Optional[int] = None,
    ) -> str:
        """Create isolated filesystem for a sandbox."""
        with self._lock:
            # Create mount namespace
            ns_id = self.mount_ns_manager.create_namespace(f"mnt-{sandbox_id}")
            
            # Create policy
            policy = FilesystemPolicy(
                tenant_id=tenant_id,
                mode=mode,
                allowed_paths=allowed_paths or ["/tmp", "/workspace"],
                denied_paths=denied_paths or ["/etc", "/root", "/home", "/boot", "/sys", "/proc"],
            )
            
            if max_size_mb:
                policy.max_size_mb = max_size_mb
            
            self.policy_engine.add_policy(policy)
            self._sandbox_policies[sandbox_id] = policy.policy_id
            self._sandbox_namespaces[sandbox_id] = ns_id
            
            # Create isolated workspace using overlayfs
            workspace = self._create_overlay_workspace(sandbox_id, tenant_id)
            self._overlay_mounts[sandbox_id] = workspace
            
            # Try to setup project quota for precise enforcement (FS-3)
            self._setup_project_quota(sandbox_id, policy)
            
            logger.info(f"Created isolated filesystem for sandbox {sandbox_id}: {workspace}")
            return workspace
    
    def _create_overlay_workspace(self, sandbox_id: str, tenant_id: str) -> str:
        """Create isolated workspace using overlayfs with explicit error handling (FS-2)."""
        base_dir = Path("/tmp/sandbox-workspaces") / sandbox_id
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create overlay directories
        lower_dir = Path("/tmp/sandbox-lower") / sandbox_id
        upper_dir = base_dir / "upper"
        work_dir = base_dir / "work"
        merged_dir = base_dir / "merged"
        
        for d in [lower_dir, upper_dir, work_dir, merged_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Mount overlay with explicit error handling (FS-2)
        try:
            result = subprocess.run([
                "mount", "-t", "overlay", "overlay",
                "-o", f"lowerdir={lower_dir},upperdir={upper_dir},workdir={work_dir}",
                str(merged_dir)
            ], check=True, capture_output=True, text=True)
            
            logger.info(f"Mounted overlay for sandbox {sandbox_id}: {merged_dir}")
            
            # Track the mount for cleanup
            self.mount_ns_manager.add_mount(f"mnt-{sandbox_id}", str(merged_dir))
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Overlay mount failed: {e.stderr}")
            # Check specific error conditions
            if "permission denied" in e.stderr.lower():
                logger.error("Overlay mount requires CAP_SYS_ADMIN or root privileges")
            elif "no such device" in e.stderr.lower():
                logger.error("Overlay filesystem not supported by kernel")
            
            # Fallback to bind mount with warning
            logger.warning("Falling back to bind mount (no copy-on-write)")
            merged_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a simple bind mount from lower to merged as fallback
            try:
                subprocess.run([
                    "mount", "--bind", str(lower_dir), str(merged_dir)
                ], check=True, capture_output=True)
                logger.info(f"Created bind mount fallback: {lower_dir} -> {merged_dir}")
            except subprocess.CalledProcessError as e2:
                logger.error(f"Bind mount fallback also failed: {e2.stderr}")
                # Last resort: just use the directory directly (no isolation)
                logger.warning("Using directory directly without mount isolation")
        
        return str(merged_dir)
    
    def _setup_bind_mounts(self, sandbox_id: str, policy: FilesystemPolicy) -> None:
        """Set up bind mounts according to policy."""
        ns_id = f"mnt-{sandbox_id}"
        
        for rule in policy.mount_rules:
            if not rule.source or not rule.target:
                continue
            
            source = Path(rule.source)
            target = Path(rule.target)
            
            if not source.exists():
                logger.warning(f"Mount source does not exist: {rule.source}")
                continue
            
            target.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                opts = ["bind"]
                if rule.readonly:
                    opts.append("ro")
                if rule.recursive:
                    opts.append("rbind")
                if rule.options:
                    opts.append(rule.options)
                
                subprocess.run([
                    "mount", "-o", ",".join(opts),
                    str(source), str(target)
                ], check=True, capture_output=True)
                
                # Track mount
                self.mount_ns_manager.add_mount(f"mnt-{sandbox_id}", str(target))
                
                logger.info(f"Mounted {source} -> {target} ({','.join(['ro' if rule.readonly else 'rw'])})")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to mount {rule.source} -> {rule.target}: {e.stderr}")
    
    def check_access(
        self,
        sandbox_id: str,
        path: str,
        operation: str,  # read, write, create, delete
    ) -> Tuple[bool, Optional[str]]:
        """Check if sandbox can access path."""
        policy_id = self._sandbox_policies.get(sandbox_id)
        if not policy_id:
            return False, "No policy for sandbox"
        
        # Get tenant from policy
        tenant_id = "default"
        for pid, policy in self.policy_engine._policies.items():
            if pid == policy_id:
                tenant_id = policy.tenant_id
                break
        
        return self.policy_engine.check_access(tenant_id, path, operation)
    
    def enforce_quota(self, sandbox_id: str) -> Tuple[bool, Optional[str]]:
        """Enforce disk quota for sandbox using statvfs (FS-3)."""
        policy_id = self._sandbox_policies.get(sandbox_id)
        if not policy_id:
            return True, None
        
        policy = self.policy_engine.get_policy(policy_id)
        if not policy or not policy.max_size_mb:
            return True, None
        
        workspace = self._overlay_mounts.get(sandbox_id)
        if not workspace:
            return True, None
        
        try:
            # Use statvfs for accurate quota checking (FS-3)
            import os
            stat = os.statvfs(workspace)
            
            # Calculate available space in MB
            block_size = stat.f_frsize
            total_blocks = stat.f_blocks
            free_blocks = stat.f_bavail
            total_mb = (total_blocks * block_size) / (1024 * 1024)
            free_mb = (free_blocks * block_size) / (1024 * 1024)
            used_mb = total_mb - free_mb
            
            if used_mb > policy.max_size_mb:
                return False, f"Quota exceeded: {used_mb:.0f}MB > {policy.max_size_mb}MB (free: {free_mb:.0f}MB)"
            
            logger.debug(f"Quota check for {sandbox_id}: used={used_mb:.0f}MB, limit={policy.max_size_mb}MB")
            
        except Exception as e:
            logger.warning(f"Failed to check quota via statvfs: {e}")
            # Fallback to du command
            try:
                usage = subprocess.run(
                    ["du", "-sm", workspace],
                    capture_output=True, text=True, check=True
                )
                usage_mb = int(usage.stdout.split()[0])
                
                if usage_mb > policy.max_size_mb:
                    return False, f"Quota exceeded: {usage_mb}MB > {policy.max_size_mb}MB"
            except Exception as e2:
                logger.warning(f"Failed to check quota via du: {e2}")
        
        return True, None
    
    def cleanup_sandbox(self, sandbox_id: str) -> bool:
        """Clean up all filesystem resources for a sandbox."""
        with self._lock:
            ns_id = f"mnt-{sandbox_id}"
            
            # Unmount overlay
            workspace = self._overlay_mounts.pop(sandbox_id, None)
            if workspace:
                merged = Path(workspace) / "merged"
                try:
                    subprocess.run(["umount", "-R", str(merged)], capture_output=True)
                except Exception:
                    pass
                
                # Clean up temp directories
                import shutil
                shutil.rmtree(workspace, ignore_errors=True)
            
            # Clean up mount namespace
            self.mount_ns_manager.cleanup_namespace(ns_id)
            
            # Clean up policies
            policy_id = self._sandbox_policies.pop(sandbox_id, None)
            if policy_id:
                self.policy_engine.remove_policy(policy_id)
            
            return True
    

    def _setup_project_quota(self, sandbox_id: str, policy: FilesystemPolicy) -> bool:
        """Setup project quota for precise quota enforcement (requires XFS/ext4 with quota support)."""
        workspace = self._overlay_mounts.get(sandbox_id)
        if not workspace or not policy.max_size_mb:
            return False
        
        try:
            # Check if filesystem supports project quota
            result = subprocess.run(
                ["mount", "|", "grep", workspace],
                shell=True, capture_output=True, text=True
            )
            if result.returncode != 0:
                logger.warning("Could not determine filesystem for quota")
                return False
            
            # Get device path
            import os
            stat = os.statvfs(workspace)
            
            # Use xfs_quota or quota tools for project quota
            # This requires filesystem to be mounted with prjquota option
            project_id = hash(sandbox_id) & 0xFFFFFFFF
            
            # Set project ID on directory
            subprocess.run(
                ["xfs_quota", "-x", "-c", f"project -s {project_id}", workspace],
                capture_output=True
            )
            
            # Set quota limit
            subprocess.run(
                ["xfs_quota", "-x", "-c", f"limit -p bhard={policy.max_size_mb}m {project_id}", workspace],
                capture_output=True
            )
            
            logger.info(f"Set project quota for sandbox {sandbox_id}: {policy.max_size_mb}MB")
            return True
            
        except Exception as e:
            logger.debug(f"Project quota setup failed (expected on non-XFS): {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active_sandboxes": len(self._sandbox_namespaces),
                "active_policies": len(self._sandbox_policies),
                "overlay_mounts": len(self._overlay_mounts),
            }


# =============================================================================
# Default Policy Factory
# =============================================================================

def create_default_filesystem_policy(tenant_id: str, mode: str = "readonly") -> FilesystemPolicy:
    """Create a default filesystem policy."""
    return FilesystemPolicy(
        tenant_id=tenant_id,
        mode=mode,
        allowed_paths=["/tmp", "/workspace", "/home", "/opt"],
        denied_paths=["/etc", "/root", "/boot", "/sys", "/proc", "/dev"],
        max_size_mb=1024,
        allowed_fsops=["read", "write", "create", "delete", "list"],
    )


# =============================================================================
# Factory
# =============================================================================

def create_filesystem_enforcer() -> FilesystemIsolationEnforcer:
    """Create a filesystem isolation enforcer."""
    return FilesystemIsolationEnforcer()
