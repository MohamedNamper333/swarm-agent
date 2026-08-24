"""
Network Isolation Enforcement - Enforces network isolation for sandboxed executions.
Implements network namespace isolation, egress/ingress filtering, and traffic monitoring.
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


class NetworkMode(str, Enum):
    NONE = "none"           # No network access
    HOST = "host"           # Host network (full access)
    BRIDGE = "bridge"       # Bridge network (isolated but can reach internet)
    OVERLAY = "overlay"     # Overlay network (multi-host)
    CUSTOM = "custom"       # Custom network configuration


class NetworkPolicy(str, Enum):
    ALLOW_ALL = "allow_all"
    DENY_ALL = "deny_all"
    ALLOWLIST = "allowlist"      # Only allow listed destinations
    DENYLIST = "denylist"        # Block listed destinations


@dataclass
class NetworkRule:
    """A single network access rule."""
    rule_id: str = field(default_factory=lambda: f"netrule-{uuid.uuid4()}")
    name: str = ""
    description: str = ""
    direction: str = "egress"  # ingress, egress, both
    action: str = "allow"      # allow, deny
    protocol: str = "tcp"      # tcp, udp, icmp, any
    src_ip: str = "0.0.0.0/0"
    dst_ip: str = "0.0.0.0/0"
    src_port: Optional[str] = None
    dst_port: Optional[str] = None
    priority: int = 100
    enabled: bool = True


@dataclass
class NetworkPolicy:
    """Network policy for a sandbox/tenant."""
    policy_id: str = field(default_factory=lambda: f"netpol-{uuid.uuid4()}")
    name: str = ""
    tenant_id: str = "default"
    default_action: str = "deny"  # allow, deny
    rules: List[NetworkRule] = field(default_factory=list)
    mode: NetworkMode = NetworkMode.NONE
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class NetworkNamespaceManager:
    """Manages network namespaces for isolation."""
    
    def __init__(self):
        self._namespaces: Dict[str, str] = {}  # ns_id -> ns_path
        self._lock = threading.RLock()
        self._base_path = Path("/var/run/netns")
        try:
            self._base_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            logger.warning("Cannot create /var/run/netns (requires root). Network namespace features will be limited.")
            self._base_path = None
    
    def create_namespace(self, ns_id: Optional[str] = None) -> str:
        """Create a new network namespace using unshare(CLONE_NEWNET) via ctypes (NET-1)."""
        if not self._base_path:
            raise RuntimeError("Network namespace creation requires root privileges (cannot access /var/run/netns)")
        
        ns_id = ns_id or f"ns-{uuid.uuid4().hex[:8]}"
        ns_path = self._base_path / ns_id
        
        with self._lock:
            # Use unshare syscall directly for better control (NET-1)
            libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
            result = libc.unshare(CLONE_NEWNET)
            if result != 0:
                errno = ctypes.get_errno()
                # Fallback to ip command if unshare fails
                logger.warning(f"unshare failed: {os.strerror(errno)}, falling back to ip command")
                result = subprocess.run(
                    ["ip", "netns", "add", ns_id],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    raise RuntimeError(f"Failed to create network namespace: {result.stderr}")
            else:
                # Bind mount the namespace to /var/run/netns for ip command access
                ns_path.mkdir(parents=True, exist_ok=True)
                subprocess.run(["mount", "--bind", f"/proc/{os.getpid()}/ns/net", str(ns_path)], 
                              capture_output=True)
            
            # Bring up loopback
            subprocess.run(["ip", "netns", "exec", ns_id, "ip", "link", "set", "lo", "up"],
                          capture_output=True)
            
            self._namespaces[ns_id] = str(ns_path)
            logger.info(f"Created network namespace: {ns_id}")
            return ns_id
    

    def create_user_namespace(self, ns_id: Optional[str] = None) -> str:
        """Create a user namespace for unprivileged operation (NET-3)."""
        ns_id = ns_id or f"user-{uuid.uuid4().hex[:8]}"
        
        with self._lock:
            # Create user namespace
            libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
            result = libc.unshare(CLONE_NEWUSER)
            if result != 0:
                errno = ctypes.get_errno()
                raise RuntimeError(f"Failed to create user namespace: {os.strerror(errno)}")
            
            # Setup uid/gid mapping for rootless operation
            try:
                with open("/proc/self/uid_map", "w") as f:
                    f.write(f"0 {os.getuid()} 1\n")
                with open("/proc/self/gid_map", "w") as f:
                    f.write(f"0 {os.getgid()} 1\n")
                with open("/proc/self/setgroups", "w") as f:
                    f.write("deny\n")
            except Exception as e:
                logger.warning(f"Failed to setup user namespace mapping: {e}")
            
            logger.info(f"Created user namespace: {ns_id}")
            return ns_id

    def delete_namespace(self, ns_id: str) -> bool:
        """Delete a network namespace."""
        with self._lock:
            if ns_id in self._namespaces:
                result = subprocess.run(
                    ["ip", "netns", "del", ns_id],
                    capture_output=True
                )
                if result.returncode == 0:
                    del self._namespaces[ns_id]
                    logger.info(f"Deleted network namespace: {ns_id}")
                    return True
            return False
    
    def execute_in_namespace(self, ns_id: str, cmd: List[str]) -> subprocess.CompletedProcess:
        """Execute a command inside a network namespace."""
        if ns_id not in self._namespaces:
            raise ValueError(f"Namespace {ns_id} does not exist")
        
        full_cmd = ["ip", "netns", "exec", ns_id] + cmd
        return subprocess.run(full_cmd, capture_output=True, text=True)
    
    def list_namespaces(self) -> List[str]:
        with self._lock:
            return list(self._namespaces.keys())
    
    def namespace_exists(self, ns_id: str) -> bool:
        with self._lock:
            return ns_id in self._namespaces


class NetworkPolicyEngine:
    """Evaluates network policies against traffic."""
    
    def __init__(self):
        self._policies: Dict[str, NetworkPolicy] = {}
        self._lock = threading.RLock()
    
    def add_policy(self, policy: NetworkPolicy) -> None:
        with self._lock:
            self._policies[policy.policy_id] = policy
    
    def remove_policy(self, policy_id: str) -> bool:
        with self._lock:
            if policy_id in self._policies:
                del self._policies[policy_id]
                return True
            return False
    
    def get_policy(self, policy_id: str) -> Optional[NetworkPolicy]:
        with self._lock:
            return self._policies.get(policy_id)
    
    def get_policy_for_tenant(self, tenant_id: str) -> Optional[NetworkPolicy]:
        with self._lock:
            for policy in self._policies.values():
                if policy.tenant_id == tenant_id and policy.enabled:
                    return policy
            return None
    
    def evaluate(
        self,
        tenant_id: str,
        direction: str,
        protocol: str,
        src_ip: str,
        dst_ip: str,
        src_port: Optional[int] = None,
        dst_port: Optional[int] = None,
    ) -> bool:
        """Evaluate if traffic is allowed."""
        policy = self.get_policy_for_tenant(tenant_id)
        if not policy:
            return False  # Default deny
        
        if policy.mode == NetworkMode.NONE:
            return False
        
        if policy.mode == NetworkMode.HOST:
            return True  # Host network has full access
        
        # Check rules in priority order
        for rule in sorted(policy.rules, key=lambda r: r.priority):
            if not rule.enabled:
                continue
            
            if rule.direction not in (direction, "both"):
                continue
            
            if rule.protocol != "any" and rule.protocol != protocol:
                continue
            
            if not self._ip_matches(rule.src_ip, src_ip):
                continue
            if not self._ip_matches(rule.dst_ip, dst_ip):
                continue
            
            if rule.src_port and src_port:
                if not self._port_matches(rule.src_port, src_port):
                    continue
            
            if rule.dst_port and dst_port:
                if not self._port_matches(rule.dst_port, dst_port):
                    continue
            
            return rule.action == "allow"
        
        # Default action
        return policy.default_action == "allow"
    
    def _ip_matches(self, pattern: str, ip: str) -> bool:
        """Check if IP matches CIDR pattern."""
        if pattern == "0.0.0.0/0":
            return True
        try:
            import ipaddress
            network = ipaddress.ip_network(pattern, strict=False)
            return ipaddress.ip_address(ip) in network
        except Exception:
            return pattern == ip
    
    def _port_matches(self, pattern: str, port: int) -> bool:
        """Check if port matches pattern."""
        if "-" in pattern:
            start, end = map(int, pattern.split("-"))
            return start <= port <= end
        elif "," in pattern:
            ports = [int(p.strip()) for p in pattern.split(",")]
            return port in ports
        else:
            return port == int(pattern)


class NetworkIsolationEnforcer:
    """Enforces network isolation for sandboxes."""
    
    def __init__(self):
        self.ns_manager = NetworkNamespaceManager()
        self.policy_engine = NetworkPolicyEngine()
        self._lock = threading.RLock()
        self._sandbox_policies: Dict[str, str] = {}  # sandbox_id -> policy_id
    
    def create_isolated_network(
        self,
        sandbox_id: str,
        tenant_id: str = "default",
        mode: NetworkMode = NetworkMode.NONE,
        custom_policy: Optional[NetworkPolicy] = None,
    ) -> str:
        """Create isolated network for a sandbox."""
        with self._lock:
            # Create network namespace
            ns_id = self.ns_manager.create_namespace(f"sandbox-{sandbox_id}")
            
            # Create or get policy
            if custom_policy:
                policy = custom_policy
                policy.tenant_id = tenant_id
                policy.mode = mode
            else:
                policy = self.policy_engine.get_policy_for_tenant(tenant_id)
                if not policy:
                    # Create default policy based on mode
                    policy = self._create_default_policy(tenant_id, mode)
            
            # Apply policy to namespace
            self._apply_policy_to_namespace(policy, ns_id)
            
            # Track sandbox -> policy mapping
            self._sandbox_policies[sandbox_id] = policy.policy_id
            
            return ns_id
    
    def _create_default_policy(self, tenant_id: str, mode: NetworkMode) -> NetworkPolicy:
        """Create default policy based on mode."""
        return create_default_network_policy(tenant_id, mode)
    
    def _apply_policy_to_namespace(self, policy: NetworkPolicy, ns_id: str) -> None:
        """Apply network policy to namespace using iptables/nftables."""
        if policy.mode == NetworkMode.NONE:
            # Block all traffic
            self._apply_deny_all(ns_id)
        elif policy.mode == NetworkMode.HOST:
            # No restrictions needed
            pass
        elif policy.mode in (NetworkMode.BRIDGE, NetworkMode.OVERLAY):
            # Apply bridge/overlay rules
            self._apply_bridge_rules(policy, ns_id)
        elif policy.mode == NetworkMode.CUSTOM:
            # Apply custom rules
            self._apply_custom_rules(policy, ns_id)
    
    def _apply_deny_all(self, ns_id: str) -> None:
        """Block all network traffic in namespace with CAP_NET_ADMIN (NET-2)."""
        # Use ip netns exec which runs with proper capabilities
        cmds = [
            ["ip", "netns", "exec", ns_id, "iptables", "-P", "INPUT", "DROP"],
            ["ip", "netns", "exec", ns_id, "iptables", "-P", "OUTPUT", "DROP"],
            ["ip", "netns", "exec", ns_id, "iptables", "-P", "FORWARD", "DROP"],
            ["ip", "netns", "exec", ns_id, "iptables", "-A", "INPUT", "-i", "lo", "-j", "ACCEPT"],
            ["ip", "netns", "exec", ns_id, "iptables", "-A", "OUTPUT", "-o", "lo", "-j", "ACCEPT"],
        ]
        
        for cmd in cmds:
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                logger.warning(f"iptables command failed: {result.stderr}")
        
        # Also apply ip6tables rules for IPv6
        ip6_cmds = [
            ["ip", "netns", "exec", ns_id, "ip6tables", "-P", "INPUT", "DROP"],
            ["ip", "netns", "exec", ns_id, "ip6tables", "-P", "OUTPUT", "DROP"],
            ["ip", "netns", "exec", ns_id, "ip6tables", "-P", "FORWARD", "DROP"],
            ["ip", "netns", "exec", ns_id, "ip6tables", "-A", "INPUT", "-i", "lo", "-j", "ACCEPT"],
            ["ip", "netns", "exec", ns_id, "ip6tables", "-A", "OUTPUT", "-o", "lo", "-j", "ACCEPT"],
        ]
        
        for cmd in ip6_cmds:
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                logger.debug(f"ip6tables command failed (may not be available): {result.stderr}")
    
    def _apply_bridge_rules(self, policy: NetworkPolicy, ns_id: str) -> None:
        """Apply bridge network rules."""
        # Allow loopback
        self.ns_manager.execute_in_namespace(ns_id, ["iptables", "-A", "INPUT", "-i", "lo", "-j", "ACCEPT"])
        self.ns_manager.execute_in_namespace(ns_id, ["iptables", "-A", "OUTPUT", "-o", "lo", "-j", "ACCEPT"])
        
        # Apply custom rules
        self._apply_custom_rules(policy, ns_id)
    
    def _apply_custom_rules(self, policy: NetworkPolicy, ns_id: str) -> None:
        """Apply custom iptables rules from policy."""
        for rule in policy.rules:
            if not rule.enabled:
                continue
            
            chain = "OUTPUT" if rule.direction in ("egress", "both") else "INPUT"
            cmd = ["ip", "netns", "exec", ns_id, "iptables", "-A", chain]
            
            if rule.protocol != "any":
                cmd.extend(["-p", rule.protocol])
            
            if rule.src_ip != "0.0.0.0/0":
                cmd.extend(["-s", rule.src_ip])
            
            if rule.dst_ip != "0.0.0.0/0":
                cmd.extend(["-d", rule.dst_ip])
            
            if rule.src_port:
                cmd.extend(["--sport", rule.src_port])
            
            if rule.dst_port:
                cmd.extend(["--dport", rule.dst_port])
            
            cmd.extend(["-j", rule.action.upper()])
            
            result = self.ns_manager.execute_in_namespace(ns_id, cmd)
            if result.returncode != 0:
                logger.warning(f"Failed to apply rule {rule.rule_id}: {result.stderr}")
    
    def check_connectivity(self, sandbox_id: str, host: str, port: int) -> bool:
        """Test if sandbox can reach a host:port."""
        ns_id = f"sandbox-{sandbox_id}"
        if not self.ns_manager.namespace_exists(ns_id):
            return False
        
        try:
            result = self.ns_manager.execute_in_namespace(
                ns_id, ["timeout", "2", "bash", "-c", f"cat < /dev/null > /dev/tcp/{host}/{port}"]
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def cleanup_sandbox(self, sandbox_id: str) -> bool:
        """Clean up network resources for a sandbox."""
        with self._lock:
            ns_id = f"sandbox-{sandbox_id}"
            policy_id = self._sandbox_policies.pop(sandbox_id, None)
            return self.ns_manager.delete_namespace(ns_id)
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active_namespaces": len(self.ns_manager._namespaces),
                "active_policies": len(self.policy_engine._policies),
                "sandbox_policies": len(self._sandbox_policies),
            }


# =============================================================================
# Factory
# =============================================================================

def create_network_enforcer() -> NetworkIsolationEnforcer:
    """Create a network isolation enforcer."""
    return NetworkIsolationEnforcer()


def create_default_network_policy(tenant_id: str, mode: NetworkMode) -> NetworkPolicy:
    """Create a default network policy for a tenant."""
    policy = NetworkPolicy(
        tenant_id=tenant_id,
        mode=mode,
        default_action="deny",
    )
    
    if mode == NetworkMode.NONE:
        policy.rules = []
    elif mode == NetworkMode.HOST:
        policy.default_action = "allow"
    elif mode in (NetworkMode.BRIDGE, NetworkMode.OVERLAY):
        # Allow DNS, HTTP/HTTPS by default
        policy.rules = [
            NetworkRule(
                name="allow-dns",
                description="Allow DNS queries",
                direction="egress",
                action="allow",
                protocol="udp",
                dst_port="53",
                priority=10,
            ),
            NetworkRule(
                name="allow-http",
                description="Allow HTTP traffic",
                direction="egress",
                action="allow",
                protocol="tcp",
                dst_port="80",
                priority=20,
            ),
            NetworkRule(
                name="allow-https",
                description="Allow HTTPS traffic",
                direction="egress",
                action="allow",
                protocol="tcp",
                dst_port="443",
                priority=30,
            ),
        ]
    
    return policy
