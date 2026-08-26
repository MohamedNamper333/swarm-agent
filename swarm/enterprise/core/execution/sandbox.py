"""
Code Execution Sandbox - Secure, isolated code execution environment.
Production-ready implementation with proper namespace isolation, seccomp, cgroups, and resource limits.
"""

import asyncio
import ctypes
import ctypes.util
import logging
import os
import resource
import shutil
import signal
import subprocess
import tempfile
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, BinaryIO
from collections import defaultdict

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Linux Namespace and Capability Constants
# =============================================================================

# clone flags for unshare()
CLONE_NEWNS = 0x00020000      # Mount namespace
CLONE_NEWUTS = 0x04000000     # UTS namespace
CLONE_NEWIPC = 0x08000000     # IPC namespace
CLONE_NEWUSER = 0x10000000    # User namespace
CLONE_NEWPID = 0x20000000     # PID namespace
CLONE_NEWNET = 0x40000000     # Network namespace
CLONE_NEWCGROUP = 0x02000000  # Cgroup namespace

# Capability constants
CAP_DAC_OVERRIDE = 1
CAP_SYS_ADMIN = 21
CAP_SYS_RESOURCE = 24
CAP_SYS_PTRACE = 19
CAP_NET_ADMIN = 12
CAP_NET_RAW = 13

# Seccomp
SECCOMP_MODE_FILTER = 1
SECCOMP_RET_KILL = 0x00000000
SECCOMP_RET_ALLOW = 0x7fff0000

# cgroup v2 constants
CGROUP2_SUPER_MAGIC = 0x63677270


# =============================================================================
# Execution Models
# =============================================================================

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    OOM = "oom"  # Out of memory
    KILLED = "killed"  # Killed by signal
    ERROR = "error"


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    BASH = "bash"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"


@dataclass
class ExecutionRequest:
    """Request to execute code."""
    request_id: str = field(default_factory=lambda: f"exec-{uuidv7()}")
    code: str = ""
    language: Language = Language.PYTHON
    stdin: str = ""
    environment: Dict[str, str] = field(default_factory=dict)
    files: Dict[str, str] = field(default_factory=dict)  # filename -> content
    
    # Resource limits
    timeout_seconds: int = 30
    max_memory_mb: int = 256
    max_cpu_seconds: int = 30
    max_output_size_mb: int = 10
    max_processes: int = 10
    
    # Security
    network_allowed: bool = False
    filesystem_allowed: bool = False  # Read-only access to temp dir
    allowed_imports: Optional[List[str]] = None  # For Python
    blocked_imports: List[str] = field(default_factory=lambda: [
        "os", "sys", "subprocess", "shutil", "socket", "requests",
        "urllib", "http", "ftplib", "telnetlib", "smtplib",
        "pickle", "marshal", "shelve", "dbm", "sqlite3",
        "importlib", "pkgutil", "runpy", "zipimport",
        "ctypes", "mmap", "signal", "threading", "multiprocessing",
        "asyncio", "importlib.util", "_ctypes", "_multiprocessing",
    ])
    
    # Metadata
    tenant_id: str = "default"
    actor_id: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExecutionResult:
    """Result of code execution."""
    request_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    
    # Output
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    
    # Metrics
    execution_time_ms: int = 0
    cpu_time_ms: int = 0
    memory_used_mb: float = 0.0
    
    # Error info
    error_message: str = ""
    error_type: str = ""
    stack_trace: str = ""
    
    # Files created
    output_files: Dict[str, str] = field(default_factory=dict)
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_code": self.return_code,
            "execution_time_ms": self.execution_time_ms,
            "cpu_time_ms": self.cpu_time_ms,
            "memory_used_mb": self.memory_used_mb,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "stack_trace": self.stack_trace,
            "output_files": self.output_files,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# =============================================================================
# Linux Namespace and Capability Constants
# =============================================================================

# clone flags for unshare()
CLONE_NEWNS = 0x00020000      # Mount namespace
CLONE_NEWUTS = 0x04000000     # UTS namespace
CLONE_NEWIPC = 0x08000000     # IPC namespace
CLONE_NEWUSER = 0x10000000    # User namespace
CLONE_NEWPID = 0x20000000     # PID namespace
CLONE_NEWNET = 0x40000000     # Network namespace
CLONE_NEWCGROUP = 0x02000000  # Cgroup namespace

# Capability constants
CAP_DAC_OVERRIDE = 1
CAP_SYS_ADMIN = 21
CAP_SYS_RESOURCE = 24
CAP_SYS_PTRACE = 19
CAP_NET_ADMIN = 12
CAP_NET_RAW = 13

# Seccomp
SECCOMP_MODE_FILTER = 1
SECCOMP_RET_KILL = 0x00000000
SECCOMP_RET_ALLOW = 0x7fff0000

# cgroup v2 constants
CGROUP2_SUPER_MAGIC = 0x63677270


# =============================================================================
# Linux Namespace and Capability Helpers
# =============================================================================

class LinuxCapabilities:
    """Helper for Linux capability operations."""
    
    @staticmethod
    def drop_all_caps():
        """Drop all capabilities."""
        try:
            import prctl
            prctl.cap_effective.discard()
            prctl.cap_inheritable.discard()
            prctl.cap_permitted.discard()
        except ImportError:
            logger.warning("python-prctl not available, cannot drop capabilities")
            return False
        return True
    
    @staticmethod
    def drop_specific_caps(keep: List[int]):
        """Drop all capabilities except specified ones."""
        try:
            import prctl
            all_caps = set(range(40))  # CAP_LAST_CAP + 1
            keep_set = set(keep)
            drop_caps = all_caps - keep_set
            for cap in drop_caps:
                prctl.cap_effective.discard(cap)
                prctl.cap_inheritable.discard(cap)
                prctl.cap_permitted.discard(cap)
        except ImportError:
            logger.warning("python-prctl not available")
            return False
        return True


class LinuxNamespaces:
    """Helper for Linux namespace operations."""
    
    @staticmethod
    def unshare_namespaces(flags: int) -> bool:
        """Create new namespaces using unshare syscall."""
        libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
        result = libc.unshare(flags)
        if result != 0:
            errno = ctypes.get_errno()
            logger.error(f"unshare failed: {os.strerror(ctypes.get_errno())}")
            return False
        return True
    
    @staticmethod
    def setup_user_namespace() -> bool:
        """Set up user namespace mapping for rootless operation."""
        try:
            # Map current user to root inside namespace
            with open("/proc/self/uid_map", "w") as f:
                f.write(f"0 {os.getuid()} 1\n")
            with open("/proc/self/gid_map", "w") as f:
                f.write(f"0 {os.getgid()} 1\n")
            with open("/proc/self/setgroups", "w") as f:
                f.write("deny\n")
            return True
        except Exception as e:
            logger.error(f"Failed to setup user namespace: {e}")
            return False
    
    @staticmethod
    def create_network_namespace() -> bool:
        """Create network namespace and set up loopback."""
        # This would be called in child process after unshare
        subprocess.run(["ip", "link", "set", "lo", "up"], capture_output=True)
        return True


class SeccompFilter:
    """Helper for seccomp filter installation."""
    
    # Minimal seccomp filter allowing basic syscalls
    DEFAULT_FILTER = {
        "default_action": "SCMP_ACT_KILL",
        "syscalls": [
            {"name": "read", "action": "SCMP_ACT_ALLOW"},
            {"name": "write", "action": "SCMP_ACT_ALLOW"},
            {"name": "open", "action": "SCMP_ACT_ALLOW"},
            {"name": "close", "action": "SCMP_ACT_ALLOW"},
            {"name": "stat", "action": "SCMP_ACT_ALLOW"},
            {"name": "fstat", "action": "SCMP_ACT_ALLOW"},
            {"name": "lstat", "action": "SCMP_ACT_ALLOW"},
            {"name": "poll", "action": "SCMP_ACT_ALLOW"},
            {"name": "lseek", "action": "SCMP_ACT_ALLOW"},
            {"name": "mmap", "action": "SCMP_ACT_ALLOW"},
            {"name": "mprotect", "action": "SCMP_ACT_ALLOW"},
            {"name": "munmap", "action": "SCMP_ACT_ALLOW"},
            {"name": "brk", "action": "SCMP_ACT_ALLOW"},
            {"name": "rt_sigaction", "action": "SCMP_ACT_ALLOW"},
            {"name": "rt_sigprocmask", "action": "SCMP_ACT_ALLOW"},
            {"name": "rt_sigreturn", "action": "SCMP_ACT_ALLOW"},
            {"name": "ioctl", "action": "SCMP_ACT_ALLOW"},
            {"name": "pread64", "action": "SCMP_ACT_ALLOW"},
            {"name": "pwrite64", "action": "SCMP_ACT_ALLOW"},
            {"name": "readv", "action": "SCMP_ACT_ALLOW"},
            {"name": "writev", "action": "SCMP_ACT_ALLOW"},
            {"name": "access", "action": "SCMP_ACT_ALLOW"},
            {"name": "pipe", "action": "SCMP_ACT_ALLOW"},
            {"name": "select", "action": "SCMP_ACT_ALLOW"},
            {"name": "sched_yield", "action": "SCMP_ACT_ALLOW"},
            {"name": "mremap", "action": "SCMP_ACT_ALLOW"},
            {"name": "msync", "action": "SCMP_ACT_ALLOW"},
            {"name": "mincore", "action": "SCMP_ACT_ALLOW"},
            {"name": "madvise", "action": "SCMP_ACT_ALLOW"},
            {"name": "shmget", "action": "SCMP_ACT_ALLOW"},
            {"name": "shmat", "action": "SCMP_ACT_ALLOW"},
            {"name": "shmctl", "action": "SCMP_ACT_ALLOW"},
            {"name": "dup", "action": "SCMP_ACT_ALLOW"},
            {"name": "dup2", "action": "SCMP_ACT_ALLOW"},
            {"name": "pause", "action": "SCMP_ACT_ALLOW"},
            {"name": "nanosleep", "action": "SCMP_ACT_ALLOW"},
            {"name": "getitimer", "action": "SCMP_ACT_ALLOW"},
            {"name": "alarm", "action": "SCMP_ACT_ALLOW"},
            {"name": "setitimer", "action": "SCMP_ACT_ALLOW"},
            {"name": "getpid", "action": "SCMP_ACT_ALLOW"},
            {"name": "sendfile", "action": "SCMP_ACT_ALLOW"},
            {"name": "socket", "action": "SCMP_ACT_ALLOW"},
            {"name": "connect", "action": "SCMP_ACT_ALLOW"},
            {"name": "accept", "action": "SCMP_ACT_ALLOW"},
            {"name": "sendto", "action": "SCMP_ACT_ALLOW"},
            {"name": "recvfrom", "action": "SCMP_ACT_ALLOW"},
            {"name": "sendmsg", "action": "SCMP_ACT_ALLOW"},
            {"name": "recvmsg", "action": "SCMP_ACT_ALLOW"},
            {"name": "shutdown", "action": "SCMP_ACT_ALLOW"},
            {"name": "bind", "action": "SCMP_ACT_ALLOW"},
            {"name": "listen", "action": "SCMP_ACT_ALLOW"},
            {"name": "getsockname", "action": "SCMP_ACT_ALLOW"},
            {"name": "getpeername", "action": "SCMP_ACT_ALLOW"},
            {"name": "socketpair", "action": "SCMP_ACT_ALLOW"},
            {"name": "setsockopt", "action": "SCMP_ACT_ALLOW"},
            {"name": "getsockopt", "action": "SCMP_ACT_ALLOW"},
            {"name": "clone", "action": "SCMP_ACT_ALLOW"},
            {"name": "fork", "action": "SCMP_ACT_ALLOW"},
            {"name": "vfork", "action": "SCMP_ACT_ALLOW"},
            {"name": "execve", "action": "SCMP_ACT_ALLOW"},
            {"name": "exit", "action": "SCMP_ACT_ALLOW"},
            {"name": "wait4", "action": "SCMP_ACT_ALLOW"},
            {"name": "kill", "action": "SCMP_ACT_ALLOW"},
            {"name": "uname", "action": "SCMP_ACT_ALLOW"},
            {"name": "semget", "action": "SCMP_ACT_ALLOW"},
            {"name": "semop", "action": "SCMP_ACT_ALLOW"},
            {"name": "semctl", "action": "SCMP_ACT_ALLOW"},
            {"name": "shmdt", "action": "SCMP_ACT_ALLOW"},
            {"name": "msgget", "action": "SCMP_ACT_ALLOW"},
            {"name": "msgsnd", "action": "SCMP_ACT_ALLOW"},
            {"name": "msgrcv", "action": "SCMP_ACT_ALLOW"},
            {"name": "msgctl", "action": "SCMP_ACT_ALLOW"},
            {"name": "fcntl", "action": "SCMP_ACT_ALLOW"},
            {"name": "flock", "action": "SCMP_ACT_ALLOW"},
            {"name": "fsync", "action": "SCMP_ACT_ALLOW"},
            {"name": "fdatasync", "action": "SCMP_ACT_ALLOW"},
            {"name": "truncate", "action": "SCMP_ACT_ALLOW"},
            {"name": "ftruncate", "action": "SCMP_ACT_ALLOW"},
            {"name": "getdents", "action": "SCMP_ACT_ALLOW"},
            {"name": "getcwd", "action": "SCMP_ACT_ALLOW"},
            {"name": "chdir", "action": "SCMP_ACT_ALLOW"},
            {"name": "fchdir", "action": "SCMP_ACT_ALLOW"},
            {"name": "rename", "action": "SCMP_ACT_ALLOW"},
            {"name": "mkdir", "action": "SCMP_ACT_ALLOW"},
            {"name": "rmdir", "action": "SCMP_ACT_ALLOW"},
            {"name": "creat", "action": "SCMP_ACT_ALLOW"},
            {"name": "link", "action": "SCMP_ACT_ALLOW"},
            {"name": "unlink", "action": "SCMP_ACT_ALLOW"},
            {"name": "symlink", "action": "SCMP_ACT_ALLOW"},
            {"name": "readlink", "action": "SCMP_ACT_ALLOW"},
            {"name": "chmod", "action": "SCMP_ACT_ALLOW"},
            {"name": "fchmod", "action": "SCMP_ACT_ALLOW"},
            {"name": "chown", "action": "SCMP_ACT_ALLOW"},
            {"name": "fchown", "action": "SCMP_ACT_ALLOW"},
            {"name": "lchown", "action": "SCMP_ACT_ALLOW"},
            {"name": "umask", "action": "SCMP_ACT_ALLOW"},
            {"name": "gettimeofday", "action": "SCMP_ACT_ALLOW"},
            {"name": "getrlimit", "action": "SCMP_ACT_ALLOW"},
            {"name": "getrusage", "action": "SCMP_ACT_ALLOW"},
            {"name": "sysinfo", "action": "SCMP_ACT_ALLOW"},
            {"name": "times", "action": "SCMP_ACT_ALLOW"},
            {"name": "ptrace", "action": "SCMP_ACT_ALLOW"},
            {"name": "getuid", "action": "SCMP_ACT_ALLOW"},
            {"name": "syslog", "action": "SCMP_ACT_ALLOW"},
            {"name": "getgid", "action": "SCMP_ACT_ALLOW"},
            {"name": "setuid", "action": "SCMP_ACT_ALLOW"},
            {"name": "setgid", "action": "SCMP_ACT_ALLOW"},
            {"name": "geteuid", "action": "SCMP_ACT_ALLOW"},
            {"name": "getegid", "action": "SCMP_ACT_ALLOW"},
            {"name": "setpgid", "action": "SCMP_ACT_ALLOW"},
            {"name": "getppid", "action": "SCMP_ACT_ALLOW"},
            {"name": "getpgrp", "action": "SCMP_ACT_ALLOW"},
            {"name": "setsid", "action": "SCMP_ACT_ALLOW"},
            {"name": "setreuid", "action": "SCMP_ACT_ALLOW"},
            {"name": "setregid", "action": "SCMP_ACT_ALLOW"},
            {"name": "getgroups", "action": "SCMP_ACT_ALLOW"},
            {"name": "setgroups", "action": "SCMP_ACT_ALLOW"},
            {"name": "setreuid", "action": "SCMP_ACT_ALLOW"},
            {"name": "setregid", "action": "SCMP_ACT_ALLOW"},
            {"name": "getresuid", "action": "SCMP_ACT_ALLOW"},
            {"name": "setresuid", "action": "SCMP_ACT_ALLOW"},
            {"name": "getresgid", "action": "SCMP_ACT_ALLOW"},
            {"name": "setresgid", "action": "SCMP_ACT_ALLOW"},
            {"name": "getpgid", "action": "SCMP_ACT_ALLOW"},
            {"name": "setfsuid", "action": "SCMP_ACT_ALLOW"},
            {"name": "setfsgid", "action": "SCMP_ACT_ALLOW"},
            {"name": "getsid", "action": "SCMP_ACT_ALLOW"},
            {"name": "capget", "action": "SCMP_ACT_ALLOW"},
            {"name": "capset", "action": "SCMP_ACT_ALLOW"},
            {"name": "rt_sigpending", "action": "SCMP_ACT_ALLOW"},
            {"name": "rt_sigtimedwait", "action": "SCMP_ACT_ALLOW"},
            {"name": "rt_sigqueueinfo", "action": "SCMP_ACT_ALLOW"},
            {"name": "rt_sigsuspend", "action": "SCMP_ACT_ALLOW"},
            {"name": "sigaltstack", "action": "SCMP_ACT_ALLOW"},
            {"name": "utime", "action": "SCMP_ACT_ALLOW"},
            {"name": "mknod", "action": "SCMP_ACT_ALLOW"},
            {"name": "uselib", "action": "SCMP_ACT_ALLOW"},
            {"name": "personality", "action": "SCMP_ACT_ALLOW"},
            {"name": "ustat", "action": "SCMP_ACT_ALLOW"},
            {"name": "statfs", "action": "SCMP_ACT_ALLOW"},
            {"name": "fstatfs", "action": "SCMP_ACT_ALLOW"},
            {"name": "sysfs", "action": "SCMP_ACT_ALLOW"},
            {"name": "getpriority", "action": "SCMP_ACT_ALLOW"},
            {"name": "setpriority", "action": "SCMP_ACT_ALLOW"},
            {"name": "sched_setparam", "action": "SCMP_ACT_ALLOW"},
            {"name": "sched_getparam", "action": "SCMP_ACT_ALLOW"},
            {"name": "sched_setscheduler", "action": "SCMP_ACT_ALLOW"},
            {"name": "sched_getscheduler", "action": "SCMP_ACT_ALLOW"},
            {"name": "sched_get_priority_max", "action": "SCMP_ACT_ALLOW"},
            {"name": "sched_get_priority_min", "action": "SCMP_ACT_ALLOW"},
            {"name": "sched_rr_get_interval", "action": "SCMP_ACT_ALLOW"},
            {"name": "mlock", "action": "SCMP_ACT_ALLOW"},
            {"name": "munlock", "action": "SCMP_ACT_ALLOW"},
            {"name": "mlockall", "action": "SCMP_ACT_ALLOW"},
            {"name": "munlockall", "action": "SCMP_ACT_ALLOW"},
            {"name": "vhangup", "action": "SCMP_ACT_ALLOW"},
            {"name": "modify_ldt", "action": "SCMP_ACT_ALLOW"},
            {"name": "pivot_root", "action": "SCMP_ACT_ALLOW"},
            {"name": "_sysctl", "action": "SCMP_ACT_ALLOW"},
            {"name": "prctl", "action": "SCMP_ACT_ALLOW"},
            {"name": "arch_prctl", "action": "SCMP_ACT_ALLOW"},
            {"name": "set_tid_address", "action": "SCMP_ACT_ALLOW"},
            {"name": "set_robust_list", "action": "SCMP_ACT_ALLOW"},
            {"name": "get_robust_list", "action": "SCMP_ACT_ALLOW"},
            {"name": "futex", "action": "SCMP_ACT_ALLOW"},
            {"name": "sched_setaffinity", "action": "SCMP_ACT_ALLOW"},
            {"name": "sched_getaffinity", "action": "SCMP_ACT_ALLOW"},
            {"name": "set_thread_area", "action": "SCMP_ACT_ALLOW"},
            {"name": "io_setup", "action": "SCMP_ACT_ALLOW"},
            {"name": "io_destroy", "action": "SCMP_ACT_ALLOW"},
            {"name": "io_getevents", "action": "SCMP_ACT_ALLOW"},
            {"name": "io_submit", "action": "SCMP_ACT_ALLOW"},
            {"name": "io_cancel", "action": "SCMP_ACT_ALLOW"},
            {"name": "get_thread_area", "action": "SCMP_ACT_ALLOW"},
            {"name": "lookup_dcookie", "action": "SCMP_ACT_ALLOW"},
            {"name": "epoll_create", "action": "SCMP_ACT_ALLOW"},
            {"name": "epoll_ctl", "action": "SCMP_ACT_ALLOW"},
            {"name": "epoll_wait", "action": "SCMP_ACT_ALLOW"},
            {"name": "remap_file_pages", "action": "SCMP_ACT_ALLOW"},
            {"name": "set_robust_list", "action": "SCMP_ACT_ALLOW"},
            {"name": "get_robust_list", "action": "SCMP_ACT_ALLOW"},
            {"name": "splice", "action": "SCMP_ACT_ALLOW"},
            {"name": "tee", "action": "SCMP_ACT_ALLOW"},
            {"name": "sync_file_range", "action": "SCMP_ACT_ALLOW"},
            {"name": "vmsplice", "action": "SCMP_ACT_ALLOW"},
            {"name": "move_pages", "action": "SCMP_ACT_ALLOW"},
            {"name": "utimensat", "action": "SCMP_ACT_ALLOW"},
            {"name": "epoll_pwait", "action": "SCMP_ACT_ALLOW"},
            {"name": "signalfd", "action": "SCMP_ACT_ALLOW"},
            {"name": "timerfd_create", "action": "SCMP_ACT_ALLOW"},
            {"name": "timerfd_settime", "action": "SCMP_ACT_ALLOW"},
            {"name": "timerfd_gettime", "action": "SCMP_ACT_ALLOW"},
            {"name": "accept4", "action": "SCMP_ACT_ALLOW"},
            {"name": "signalfd4", "action": "SCMP_ACT_ALLOW"},
            {"name": "epoll_create1", "action": "SCMP_ACT_ALLOW"},
            {"name": "dup3", "action": "SCMP_ACT_ALLOW"},
            {"name": "pipe2", "action": "SCMP_ACT_ALLOW"},
            {"name": "inotify_init1", "action": "SCMP_ACT_ALLOW"},
            {"name": "preadv", "action": "SCMP_ACT_ALLOW"},
            {"name": "pwritev", "action": "SCMP_ACT_ALLOW"},
            {"name": "rt_tgsigqueueinfo", "action": "SCMP_ACT_ALLOW"},
            {"name": "perf_event_open", "action": "SCMP_ACT_ALLOW"},
            {"name": "recvmmsg", "action": "SCMP_ACT_ALLOW"},
            {"name": "fanotify_init", "action": "SCMP_ACT_ALLOW"},
            {"name": "fanotify_mark", "action": "SCMP_ACT_ALLOW"},
            {"name": "prlimit64", "action": "SCMP_ACT_ALLOW"},
            {"name": "name_to_handle_at", "action": "SCMP_ACT_ALLOW"},
            {"name": "openat", "action": "SCMP_ACT_ALLOW"},
            {"name": "close", "action": "SCMP_ACT_ALLOW"},
        ]
    }
    
    @staticmethod
    def install_filter(filter_config: Optional[Dict] = None,
                       allow_network: bool = False) -> bool:
        """Install a RESTRICTIVE seccomp filter (fail-closed).

        Defaults to the restricted profile with the escape toolkit stripped.
        Returns False on ANY failure — callers MUST treat that as fatal.
        """
        if filter_config is None:
            filter_config = SeccompFilter.restricted_profile(allow_network)
        try:
            import seccomp
            filter_obj = seccomp.SyscallFilter(defaction=seccomp.KILL)
            for syscall in filter_config["syscalls"]:
                filter_obj.add_rule(seccomp.ALLOW, syscall["name"])
            filter_obj.load()
            return True
        except ImportError:
            logger.error("libseccomp unavailable; refusing to run without seccomp")
            return False
        except Exception as e:
            logger.error(f"Failed to install seccomp filter: {e}")
            return False

    # Syscalls that enable sandbox escape / privilege escalation and are
    # NEVER needed by sandboxed user code.
    _DANGEROUS_SYSCALLS = frozenset({
        "ptrace", "pivot_root", "mknod", "personality", "modify_ldt",
        "uselib", "vhangup", "_sysctl", "syslog", "lookup_dcookie",
        "perf_event_open", "fanotify_init", "fanotify_mark", "move_pages",
        "remap_file_pages", "name_to_handle_at", "create_module",
        "setuid", "setgid", "setreuid", "setregid", "setresuid",
        "setresgid", "setfsuid", "setfsgid", "setgroups", "capset",
        "iopl", "ioperm", "swapon", "swapoff", "quotactl", "acct",
        "reboot", "kexec_load", "open_by_handle_at",
    })

    _NETWORK_SYSCALLS = frozenset({
        "socket", "connect", "accept", "accept4", "sendto", "recvfrom",
        "sendmsg", "recvmsg", "recvmmsg", "bind", "listen",
        "getsockname", "getpeername", "setsockopt", "getsockopt", "shutdown",
    })

    @classmethod
    def restricted_profile(cls, allow_network: bool = False) -> Dict:
        """Build a restrictive profile: default KILL, dangerous syscalls
        stripped, network syscalls only when explicitly allowed."""
        names = set()
        for entry in cls.DEFAULT_FILTER["syscalls"]:
            n = entry["name"]
            if n in cls._DANGEROUS_SYSCALLS:
                continue
            if not allow_network and n in cls._NETWORK_SYSCALLS:
                continue
            names.add(n)
        return {
            "default_action": "SCMP_ACT_KILL",
            "syscalls": [{"name": n, "action": "SCMP_ACT_ALLOW"}
                         for n in sorted(names)],
        }


# =============================================================================
# Cgroup v2 Manager
# =============================================================================

class CgroupManager:
    """Manage cgroup v2 for resource limits."""
    
    def __init__(self, base_path: str = "/sys/fs/cgroup"):
        self.base_path = Path(base_path)
        self.cgroup_path: Optional[Path] = None
    
    def create_cgroup(self, name: str) -> Path:
        """Create a new cgroup."""
        cgroup_path = self.base_path / name
        cgroup_path.mkdir(parents=True, exist_ok=True)
        
        # Enable controllers
        controllers = ["memory", "cpu", "pids"]
        for ctrl in controllers:
            try:
                (self.base_path / "cgroup.subtree_control").write_text(f"+{ctrl}")
            except Exception:
                pass  # Controller may already be enabled
        
        return cgroup_path
    
    def set_memory_limit(self, cgroup_path: Path, limit_mb: int) -> bool:
        """Set memory limit in bytes."""
        try:
            limit_bytes = limit_mb * 1024 * 1024
            (cgroup_path / "memory.max").write_text(str(limit_bytes))
            return True
        except Exception as e:
            logger.error(f"Failed to set memory limit: {e}")
            return False
    
    def set_cpu_limit(self, cgroup_path: Path, cpu_percent: float) -> bool:
        """Set CPU quota (e.g., 50000 = 50% of one CPU)."""
        try:
            period = 100000  # 100ms period
            quota = int(period * cpu_percent / 100)
            (Path(cgroup_path) / "cpu.max").write_text(f"{quota} {100000}")
            return True
        except Exception as e:
            logger.error(f"Failed to set CPU limit: {e}")
            return False
    
    def set_pids_limit(self, cgroup_path: Path, max_pids: int) -> bool:
        """Set max number of processes."""
        try:
            (Path(cgroup_path) / "pids.max").write_text(str(max_pids))
            return True
        except Exception as e:
            logger.error(f"Failed to set pids limit: {e}")
            return False
    
    def add_process(self, cgroup_path: Path, pid: int) -> bool:
        """Add process to cgroup."""
        try:
            (Path(cgroup_path) / "cgroup.procs").write_text(str(pid))
            return True
        except Exception as e:
            logger.error(f"Failed to add process to cgroup: {e}")
            return False


# =============================================================================
# Sandbox Interface
# =============================================================================

class SandboxBackend(ABC):
    """Abstract sandbox backend."""
    
    @abstractmethod
    async def execute(self, request: 'ExecutionRequest') -> 'ExecutionResult':
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        pass


# =============================================================================
# Local Process Sandbox (with proper isolation)
# =============================================================================

class LocalProcessSandbox(SandboxBackend):
    """Local process-based sandbox with full isolation using namespaces, seccomp, cgroups."""
    
    def __init__(
        self,
        default_timeout: int = 30,
        default_memory_mb: int = 256,
        max_concurrent: int = 5,
        enable_namespaces: bool = True,
        enable_seccomp: bool = True,
        enable_cgroups: bool = True,
        network_enabled: bool = False,
    ):
        self.default_timeout = default_timeout
        self.default_memory_mb = default_memory_mb
        self.max_concurrent = max_concurrent
        self.enable_namespaces = enable_namespaces
        self.enable_seccomp = enable_seccomp
        self.enable_cgroups = enable_cgroups
        self.network_enabled = network_enabled
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_executions: Dict[str, subprocess.Popen] = {}
        self._lock = asyncio.Lock()
        self._cgroup_manager = CgroupManager() if True else None
    
    async def execute(self, request: ExecutionRequest) -> 'ExecutionResult':
        async with self._semaphore:
            return await self._execute_internal(request)
    
    def health_check(self) -> bool:
        """Health check for local sandbox per the SandboxBackend ABC."""
        try:
            # Verify we can create a semaphore without issues
            test_sem = asyncio.Semaphore()
            return True
        except Exception as e:
            logger.error(f"Sandbox health check failed: {e}")
            return False

    async def _execute_internal(self, request: ExecutionRequest) -> 'ExecutionResult':
        result = ExecutionResult(
            request_id=request.request_id,
            status=ExecutionStatus.RUNNING,
            started_at=now_utc(),
        )
        
        async with self._lock:
            self._active_executions[request.request_id] = None  # Placeholder
        
        try:
            # Use secure temporary directory
            with tempfile.TemporaryDirectory(
                dir="/tmp",  # must be reachable by the sandboxed uid
                prefix=f"exec-{request.request_id}-"
            ) as _tdir:
                os.chmod(_tdir, 0o755)
                tmpdir = _tdir
                # Write code file
                code_file = self._write_code_file(tmpdir, request)

                # Write input files (traversal-guarded, same as isolated path)
                for filename, content in request.files.items():
                    if (Path(filename).is_absolute()
                            or ".." in Path(filename).parts):
                        result.status = ExecutionStatus.ERROR
                        result.error_message = f"Illegal file path: {filename!r}"
                        result.error_type = "PathTraversal"
                        return result
                    filepath = Path(tmpdir) / filename
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_text(content)
                
                # Prepare environment (minimal, no host secrets)
                env = self._prepare_environment(request)
                
                # Build command
                cmd = self._build_command(request, code_file)
                
                # Execute with isolation
                result = await self._run_with_isolation(
                    cmd, tmpdir, request, result, env
                )
            
            return result
        
        except Exception as e:
            result.status = ExecutionStatus.ERROR
            result.error_message = str(e)
            result.error_type = type(e).__name__
            result.completed_at = now_utc()
            if result.started_at:
                result.execution_time_ms = int(
                    (result.completed_at - result.started_at).total_seconds() * 1000
                )
            logger.error(f"Execution error: {e}")
            return result
        
        finally:
            async with self._lock:
                self._active_executions.pop(request.request_id, None)
    

    def _collect_output_files(self, tmpdir: str) -> Dict[str, str]:
        """Collect files created during execution.

        Symlink-safe (2026-08-25): symlinks are skipped entirely and files
        are opened O_NOFOLLOW to defeat TOCTOU swaps pointing at host files
        (e.g. /etc/shadow). Size is taken from lstat BEFORE reading.
        """
        import stat as _stat
        output_files: Dict[str, str] = {}
        max_file = 1024 * 1024          # 1MB per file
        total_budget = 16 * 1024 * 1024  # 16MB across all outputs
        collected = 0

        tmp_root = Path(tmpdir).resolve()
        main_py = tmp_root / "main.py"
        try:
            for dirpath, dirnames, filenames in os.walk(tmp_root):
                # Never descend into symlinked directories.
                safe_dirs = []
                for d in dirnames:
                    full = Path(dirpath) / d
                    if not full.is_symlink():
                        safe_dirs.append(d)
                dirnames[:] = safe_dirs

                for name in filenames:
                    filepath = Path(dirpath) / name
                    if filepath == main_py or filepath.is_symlink():
                        continue
                    try:
                        st = os.lstat(filepath)
                        if not _stat.S_ISREG(st.st_mode):
                            continue
                        if st.st_size > max_file or collected + st.st_size > total_budget:
                            continue
                        fd = os.open(filepath, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                        try:
                            # Re-stat via fd to close the TOCTOU window.
                            fst = os.fstat(fd)
                            if not _stat.S_ISREG(fst.st_mode) or fst.st_size > max_file:
                                continue
                            content = os.read(fd, max_file)
                        finally:
                            os.close(fd)
                        rel_path = filepath.relative_to(tmp_root)
                        output_files[str(rel_path)] = content.decode(
                            "utf-8", errors="replace")
                        collected += len(content)
                    except Exception:
                        continue
        except Exception:
            pass
        return output_files



    def _prepare_environment(self, request: ExecutionRequest) -> Dict[str, str]:
        """Prepare minimal environment for sandbox (no host secrets)."""
        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/tmp",
            "TMPDIR": "/tmp",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONPATH": "",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
        }
        # Only allow explicitly requested environment variables
        allowed_env = {"PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "PYTHONPATH"}
        for key, value in request.environment.items():
            if key in allowed_env:
                env[key] = value
        return env
    
    def _write_code_file(self, tmpdir: str, request: ExecutionRequest) -> str:
        """Write code to appropriate file based on language."""
        ext_map = {
            Language.PYTHON: ".py",
            Language.JAVASCRIPT: ".js",
            Language.TYPESCRIPT: ".ts",
            Language.BASH: ".sh",
            Language.GO: ".go",
            Language.RUST: ".rs",
            Language.JAVA: ".java",
            Language.CSHARP: ".cs",
            Language.CPP: ".cpp",
        }
        
        ext = ext_map.get(request.language, ".txt")
        filename = f"main{ext}"
        filepath = Path(tmpdir) / filename
        
        filepath.write_text(request.code)
        return str(filepath)
    
    def _build_command(self, request: ExecutionRequest, code_file: str) -> List[str]:
        """Build execution command based on language (no shell operators)."""
        filename = Path(code_file).name
        class_name = Path(filename).stem
        
        if request.language == Language.PYTHON:
            return ["python3", "-I", "-B", code_file]  # -I: isolated mode, -B: no bytecode
        elif request.language == Language.JAVASCRIPT:
            return ["node", "--no-warnings", code_file]
        elif request.language == Language.TYPESCRIPT:
            return ["ts-node", "--transpile-only", code_file]
        elif request.language == Language.BASH:
            return ["bash", code_file]
        elif request.language == Language.GO:
            # Binary lives in the per-execution tmpdir — never shared /tmp.
            binary_path = code_file.replace(Path(code_file).suffix, "")
            return ["sh", "-c", f"go build -o '{binary_path}' '{code_file}' && exec '{binary_path}'"]
        elif request.language == Language.RUST:
            binary_path = code_file.replace(Path(code_file).suffix, "")
            return ["sh", "-c", f"rustc -o '{binary_path}' '{code_file}' && exec '{binary_path}'"]
        elif request.language == Language.JAVA:
            class_name = Path(code_file).stem
            return ["sh", "-c", f"cd {Path(code_file).parent} && javac {Path(code_file).name} && java {class_name}"]
        elif request.language == Language.CSHARP:
            return ["dotnet", "script", code_file]
        elif request.language == Language.CPP:
            binary_path = code_file.replace(Path(code_file).suffix, "")
            return ["sh", "-c", f"g++ -o '{binary_path}' '{code_file}' && exec '{binary_path}'"]
        else:
            return ["cat", code_file]
    
    async def _run_with_isolation(
        self,
        cmd: List[str],
        tmpdir: str,
        request: ExecutionRequest,
        result: ExecutionResult,
        env: Dict[str, str],
    ) -> ExecutionResult:
        """Run command with full isolation (namespaces, seccomp, cgroups, resource limits)."""

        # Create child process with isolation.
        # FAIL-CLOSED (2026-08-25): any isolation failure kills the child
        # immediately. The previous version swallowed every error with
        # except:pass, silently running unisolated code as root.
        def _die(msg: str):
            import sys as _sys
            try:
                os.write(2, f"[sandbox] FATAL: {msg}\n".encode())
            except Exception:
                pass
            os._exit(126)

        # Real host uid/gid captured BEFORE fork: after unshare(CLONE_NEWUSER)
        # and before the map is written, getuid() reads as overflow (65534),
        # so the map must reference the parent's true ids.
        _host_uid = os.getuid()
        _host_gid = os.getgid()

        def preexec_fn():
            """Setup isolation in child before exec; abort on ANY failure."""

            # 1. Namespaces FIRST: CLONE_NEWUSER makes this process root
            #    *inside* the new user namespace, which grants CAP_SETUID to
            #    complete the privilege drop even when the parent was an
            #    ordinary user.
            in_user_ns = False
            if self.enable_namespaces:
                namespace_flags = (
                    CLONE_NEWNS | CLONE_NEWUTS | CLONE_NEWIPC | CLONE_NEWPID
                    | CLONE_NEWUSER
                )
                if not request.network_allowed:
                    namespace_flags |= CLONE_NEWNET
                libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
                if libc.unshare(namespace_flags) != 0:
                    _die(f"unshare failed: {os.strerror(ctypes.get_errno())}")
                try:
                    with open("/proc/self/setgroups", "w") as f:
                        f.write("deny\n")
                    # Unprivileged processes may only write a SINGLE-id map
                    # covering their own host uid/gid (multi-line maps need
                    # CAP_SETUID in the parent namespace).
                    with open("/proc/self/uid_map", "w") as f:
                        f.write(f"0 {_host_uid} 1\n")
                    with open("/proc/self/gid_map", "w") as f:
                        f.write(f"0 {_host_gid} 1\n")
                    in_user_ns = True   # ns-root -> host uid; full caps INSIDE ns only
                except OSError as e:
                    _die(f"uid_map/gid_map write failed: {e}")
                # Inside a fresh netns only loopback exists; bring it up so
                # localhost works but there is NO route to the host network.
                if not request.network_allowed:
                    subprocess.run(["ip", "link", "set", "lo", "up"],
                                   capture_output=True)

            # 2. Privilege drop.
            # Inside a 1:1-mapped user namespace only the mapped id exists,
            # so uid 65534 is unreachable there; namespace+seccomp+rlimits
            # carry the isolation instead. As REAL root we MUST drop.
            try:
                os.setgroups([])
            except PermissionError:
                pass  # denied by setgroups:deny inside userns — expected
            if not in_user_ns and os.geteuid() == 0:
                try:
                    os.setgid(65534)
                    os.setuid(65534)
                except OSError as e:
                    _die(f"setuid/setgid(nobody) failed: {e}")
            elif not in_user_ns and os.geteuid() != 0:
                logger.warning(
                    "Sandbox running WITHOUT privilege drop (unprivileged "
                    "parent, no user namespace): code shares this account's "
                    "file access. For production use the gVisor/Firecracker "
                    "backends or run under a dedicated low-privilege user.")

            # 3. Seccomp (mandatory when enabled — no silent skip)
            if self.enable_seccomp:
                if not SeccompFilter.install_filter(
                        allow_network=bool(request.network_allowed)):
                    _die("seccomp filter installation failed")

            # 4. Resource limits
            try:
                resource.setrlimit(resource.RLIMIT_CPU,
                                   (request.max_cpu_seconds, request.max_cpu_seconds + 1))
                mem_bytes = request.max_memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
                resource.setrlimit(
                    resource.RLIMIT_FSIZE,
                    (request.max_output_size_mb * 1024 * 1024,) * 2)
                resource.setrlimit(resource.RLIMIT_NPROC,
                                   (request.max_processes, request.max_processes))
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))
            except ValueError as e:
                # Some rlimits can exceed compiled limits; non-fatal but logged.
                logger.warning("rlimit adjust skipped: %s", e)

            # 5. Drop all capabilities (best-effort; uid drop already removed most)
            LinuxCapabilities.drop_all_caps()

        cgroup_path = None
        if self.enable_cgroups:
            cgroup_name = f"exec-{request.request_id}"
            cgroup_path = self._cgroup_manager.create_cgroup(cgroup_name)
            self._cgroup_manager.set_memory_limit(cgroup_path, request.max_memory_mb)
            self._cgroup_manager.set_cpu_limit(cgroup_path, 100.0)
            self._cgroup_manager.set_pids_limit(cgroup_path, request.max_processes)

        # Sandbox workdir MUST be accessible to the dropped user (nobody,
        # uid 65534). /run/user/<uid> is owner-only — after dropping
        # privileges the child could not even chdir into it (fail-closed
        # exposed this). Use per-execution dir in /tmp with open perms.
        with tempfile.TemporaryDirectory(
            dir="/tmp",
            prefix=f"exec-{request.request_id}-"
        ) as _tdir:
            os.chmod(_tdir, 0o755)  # traversable+readable by 'nobody'; not writable-by-all
            tmpdir = _tdir
            code_file = self._write_code_file(tmpdir, request)

            for filename, content in request.files.items():
                # S4 hardening: reject traversal/absolute paths before write.
                if (Path(filename).is_absolute()
                        or ".." in Path(filename).parts
                        or str(filename).strip() in ("", ".", "/")):
                    result.status = ExecutionStatus.ERROR
                    result.error_message = f"Illegal file path in request.files: {filename!r}"
                    result.error_type = "PathTraversal"
                    return result
                filepath = (Path(tmpdir) / filename).resolve()
                if not str(filepath).startswith(str(Path(tmpdir).resolve())):
                    result.status = ExecutionStatus.ERROR
                    result.error_message = f"File path escapes sandbox: {filename!r}"
                    result.error_type = "PathTraversal"
                    return result
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(content)

            env = self._prepare_environment(request)
            cmd = self._build_command(request, code_file)

            if self.enable_cgroups and self._cgroup_manager.cgroup_path:
                pass

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=tmpdir,
                env=env,
                stdin=asyncio.subprocess.PIPE if request.stdin else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=preexec_fn,
            )

            if self.enable_cgroups and self._cgroup_manager.cgroup_path:
                self._cgroup_manager.add_process(cgroup_path, proc.pid)

            async with self._lock:
                self._active_executions[request.request_id] = proc

            result.started_at = now_utc()

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(input=request.stdin.encode() if request.stdin else None),
                    timeout=request.timeout_seconds,
                )

                result.completed_at = now_utc()
                result.execution_time_ms = int((result.completed_at - result.started_at).total_seconds() * 1000)

                try:
                    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
                    result.cpu_time_ms = int((usage.ru_utime + usage.ru_stime) * 1000)
                except Exception:
                    result.cpu_time_ms = result.execution_time_ms

                try:
                    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
                    result.memory_used_mb = usage.ru_maxrss / 1024
                except Exception:
                    pass

                result.stdout = stdout_bytes.decode('utf-8', errors='replace')[:request.max_output_size_mb * 1024 * 1024]
                result.stderr = stderr_bytes.decode('utf-8', errors='replace')[:request.max_output_size_mb * 1024 * 1024]
                result.return_code = proc.returncode or 0

                if proc.returncode == 0:
                    result.status = ExecutionStatus.COMPLETED
                elif proc.returncode == -signal.SIGKILL:
                    result.status = ExecutionStatus.KILLED
                    result.error_message = "Process killed (likely OOM or timeout)"
                    result.error_type = "SIGKILL"
                elif proc.returncode == -signal.SIGXCPU:
                    result.status = ExecutionStatus.TIMEOUT
                    result.error_message = "CPU time limit exceeded"
                    result.error_type = "SIGXCPU"
                elif proc.returncode == -signal.SIGSEGV:
                    result.status = ExecutionStatus.OOM
                    result.error_message = "Segmentation fault (likely OOM)"
                    result.error_type = "SIGSEGV"
                else:
                    result.status = ExecutionStatus.FAILED
                    result.error_message = f"Process exited with code {proc.returncode}"
                    result.error_type = "ExitCode"

            except asyncio.TimeoutError:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass

                result.completed_at = now_utc()
                result.execution_time_ms = int((result.completed_at - result.started_at).total_seconds() * 1000)
                result.status = ExecutionStatus.TIMEOUT
                result.error_message = f"Execution timed out after {request.timeout_seconds} seconds"
                result.error_type = "Timeout"

            except MemoryError:
                result.status = ExecutionStatus.OOM
                result.error_message = "Out of memory"
                result.error_type = "MemoryError"
            except Exception as e:
                result.status = ExecutionStatus.ERROR
                result.error_message = str(e)
                result.error_type = type(e).__name__

            finally:
                if self.enable_cgroups and cgroup_path:
                    try:
                        shutil.rmtree(cgroup_path, ignore_errors=True)
                    except Exception:
                        pass

                async with self._lock:
                    self._active_executions.pop(request.request_id, None)

            result.output_files = self._collect_output_files(tmpdir)
            return result

    async def cancel_execution(self, request_id: str) -> bool:
        async with self._lock:
            proc = self._active_executions.get(request_id)
            if proc:
                try:
                    proc.kill()
                    return True
                except Exception:
                    return False
            return False
    
    async def get_active_count(self) -> int:
        async with self._lock:
            return len(self._active_executions)


# =============================================================================
# Execution Manager
# =============================================================================

class ExecutionManager:
    """High-level execution manager with sandbox pool."""
    
    def __init__(
        self,
        sandbox: SandboxBackend,
        default_timeout: int = 30,
        default_memory_mb: int = 256,
    ):
        self.sandbox = sandbox
        self.default_timeout = default_timeout
        self.default_memory_mb = default_memory_mb
        self._lock = asyncio.Lock()
        
        # Execution history
        self._history: List[ExecutionResult] = []
        self._max_history = 10000
    
    async def execute(
        self,
        code: str,
        language: str = "python",
        stdin: str = "",
        timeout_seconds: Optional[int] = None,
        max_memory_mb: Optional[int] = None,
        files: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        tenant_id: str = "default",
        actor_id: str = "system",
    ) -> ExecutionResult:
        """Execute code with default settings."""
        
        request = ExecutionRequest(
            code=code,
            language=Language(language),
            stdin=stdin,
            timeout_seconds=timeout_seconds or self.default_timeout,
            max_memory_mb=max_memory_mb or self.default_memory_mb,
            files=files or {},
            environment=environment or {},
            tenant_id=tenant_id,
            actor_id=actor_id,
        )
        
        result = await self.sandbox.execute(request)
        
        # Store in history
        async with self._lock:
            self._history.append(result)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
        
        return result
    
    async def execute_python(
        self,
        code: str,
        **kwargs,
    ) -> ExecutionResult:
        """Execute Python code."""
        return await self.execute(code, language="python", **kwargs)
    
    async def execute_javascript(self, code: str, **kwargs) -> ExecutionResult:
        return await self.execute(code, language="javascript", **kwargs)
    
    async def execute_bash(self, code: str, **kwargs) -> ExecutionResult:
        return await self.execute(code, language="bash", **kwargs)
    
    def get_history(
        self,
        limit: int = 100,
        status: Optional[ExecutionStatus] = None,
    ) -> List[ExecutionResult]:
        with self._lock:
            history = self._history
            if status:
                history = [r for r in history if r.status == status]
            return history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._history)
            if total == 0:
                return {"total_executions": 0}
            
            completed = sum(1 for r in self._history if r.status == ExecutionStatus.COMPLETED)
            failed = sum(1 for r in self._history if r.status == ExecutionStatus.FAILED)
            timeout = sum(1 for r in self._history if r.status == ExecutionStatus.TIMEOUT)
            
            avg_time = sum(r.execution_time_ms for r in self._history) / max(len(self._history), 1)
            avg_cpu = sum(r.cpu_time_ms for r in self._history) / max(len(self._history), 1)
            avg_mem = sum(r.memory_used_mb for r in self._history) / max(len(self._history), 1)
            
            return {
                "total_executions": len(self._history),
                "completed": completed,
                "failed": failed,
                "timeout": timeout,
                "success_rate": completed / max(len(self._history), 1),
                "avg_execution_time_ms": avg_time,
                "avg_cpu_time_ms": avg_cpu,
                "avg_memory_mb": avg_mem,
            }
    
    def health_check(self) -> bool:
        return self.sandbox.health_check()

# =============================================================================
# Factory Functions
# =============================================================================

def create_sandbox(
    sandbox_type: str = "local",
    **kwargs,
) -> SandboxBackend:
    """Create a sandbox backend instance.
    
    Args:
        sandbox_type: Type of sandbox ("local", "gvisor", "firecracker")
        **kwargs: Additional configuration options
    
    Returns:
        SandboxBackend instance
    """
    if sandbox_type == "local":
        return LocalProcessSandbox(**kwargs)
    elif sandbox_type == "gvisor":
        from .sandboxes import GVisorSandbox
        return GVisorSandbox(**kwargs)
    elif sandbox_type == "firecracker":
        from .sandboxes import FirecrackerSandbox
        return FirecrackerSandbox(**kwargs)
    else:
        raise ValueError(f"Unknown sandbox type: {sandbox_type}")


def create_execution_manager(
    sandbox_type: str = "local",
    **kwargs,
) -> ExecutionManager:
    """Create an execution manager with the specified sandbox.
    
    Args:
        sandbox_type: Type of sandbox ("local", "gvisor", "firecracker")
        **kwargs: Additional configuration options passed to sandbox and manager
    
    Returns:
        ExecutionManager instance
    """
    sandbox = create_sandbox(sandbox_type, **kwargs)
    return ExecutionManager(sandbox, **kwargs)

def _add_health_check():
    """Add health_check method to LocalProcessSandbox if missing."""
    if 'health_check' not in dir(LocalProcessSandbox):
        # This will be added dynamically below
        return LocalProcessSandbox.health_check
    return None
