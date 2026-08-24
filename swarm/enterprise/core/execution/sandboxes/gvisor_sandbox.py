"""
gVisor Sandbox Backend - Secure container isolation using gVisor (runsc).
Provides strong isolation with minimal performance overhead.
"""

import asyncio
import signal
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, BinaryIO
import logging

from ..sandbox import (
    ExecutionRequest, ExecutionResult, ExecutionStatus, Language,
    SandboxBackend, create_sandbox
)

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


@dataclass
class GVisorConfig:
    """gVisor sandbox configuration."""
    runsc_path: str = "runsc"
    root_dir: str = "/run/gvisor"
    network_enabled: bool = False
    filesystem_access: bool = False
    platform: str = "ptrace"  # ptrace, kvm, kptrace
    timeout_seconds: int = 30
    memory_limit_mb: int = 256
    cpu_limit: int = 1
    pids_limit: int = 64


class GVisorSandbox(SandboxBackend):
    """gVisor-based sandbox backend using runsc."""

    def __init__(self, config: Optional[GVisorConfig] = None):
        self.config = config or GVisorConfig()
        self._active_containers: Dict[str, subprocess.Popen] = {}
        self._lock = asyncio.Lock()
        
        # Verify runsc is available
        self._verify_runsc()
    
    def _verify_runsc(self) -> None:
        """Verify runsc is installed and working."""
        try:
            result = subprocess.run(
                [self.config.runsc_path, "version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError(f"runsc not available: {result.stderr}")
            logger.info(f"gVisor runsc version: {result.stdout.strip()}")
        except FileNotFoundError:
            raise RuntimeError(
                "runsc not found. Install gVisor: "
                "https://gvisor.dev/docs/user_guide/install/"
            )
        except Exception as e:
            raise RuntimeError(f"gVisor verification failed: {e}")

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute code in gVisor sandbox."""
        request_id = request.request_id or f"exec-{uuid.uuid4()}"
        
        result = ExecutionResult(
            request_id=request_id,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        
        # Track active container
        async with self._lock:
            self._active_containers[request_id] = None  # placeholder
        
        try:
            with tempfile.TemporaryDirectory(prefix=f"gvisor-{request_id}-") as tmpdir:
                # Write code and files
                code_file = self._write_code_file(tmpdir, request)
                
                for filename, content in request.files.items():
                    filepath = Path(tmpdir) / filename
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_text(content)
                
                # Build runsc command
                cmd = self._build_runsc_command(request, code_file, tmpdir)
                
                # Execute with limits
                result = await self._run_with_limits(
                    cmd, tmpdir, request, result
                )
            
            return result
        
        except Exception as e:
            logger.error(f"gVisor execution error: {e}")
            result.status = ExecutionStatus.ERROR
            result.error_message = str(e)
            result.error_type = type(e).__name__
            result.completed_at = datetime.now(timezone.utc)
            if result.started_at:
                result.execution_time_ms = int(
                    (result.completed_at - result.started_at).total_seconds() * 1000
                )
            return result
        
        finally:
            async with self._lock:
                self._active_containers.pop(request_id, None)

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

    def _build_runsc_command(
        self, 
        request: ExecutionRequest, 
        code_file: str, 
        tmpdir: str
    ) -> List[str]:
        """Build runsc command with security flags."""
        
        # Base runsc command
        cmd = [
            self.config.runsc_path,
            "run",
            "--platform", self.config.platform,
            "--root", self.config.root_dir,
            "--memory", f"{self.config.memory_limit_mb}M",
            "--cpus", str(self.config.cpu_limit),
            "--pids-limit", str(self.config.pids_limit),
        ]
        
        # Network isolation
        if not request.network_allowed:
            cmd.extend(["--network", "none"])
        else:
            cmd.extend(["--network", "host"])
        
        # Filesystem access
        if not request.filesystem_allowed:
            cmd.extend(["--filesystem", "none"])
        else:
            cmd.extend(["--filesystem", "ro"])
        
        # Capability dropping - minimal required capabilities
        cmd.extend([
            "--cap-drop", "ALL",
            "--cap-add", "CAP_CHOWN",
            "--cap-add", "CAP_DAC_OVERRIDE",
            "--cap-add", "CAP_FOWNER",
            "--cap-add", "CAP_SETGID",
            "--cap-add", "CAP_SETUID",
        ])
        
        # Security options
        cmd.extend([
            "--no-new-privs",
            "--readonly-rootfs",
        ])
        
        # Add seccomp profile if platform supports it
        if self.config.platform in ("ptrace", "kvm"):
            seccomp_path = self._write_seccomp_profile(tmpdir)
            cmd.extend(["--seccomp", seccomp_path])
        
        # Import restrictions for Python
        if request.language == Language.PYTHON and request.blocked_imports:
            # Create a wrapper script that blocks imports
            wrapper = self._create_import_wrapper(request)
            wrapper_path = Path(request.cwd) / "import_wrapper.py"
            wrapper_path.write_text(wrapper)
            cmd.extend(["--bind", f"{wrapper_path}:/usr/local/lib/python3.11/import_wrapper.py"])
        
        # Working directory and command
        cmd.extend(["--cwd", "/workdir"])
        
        # Language-specific command
        filename = Path(code_file).name
        lang_cmd = self._get_language_command(request.language, filename)
        cmd.extend(lang_cmd)
        
        return cmd

    def _get_language_command(self, language: Language, filename: str) -> List[str]:
        """Get language-specific execution command."""
        commands = {
            Language.PYTHON: ["python3", filename],
            Language.JAVASCRIPT: ["node", filename],
            Language.TYPESCRIPT: ["ts-node", filename],
            Language.BASH: ["bash", filename],
            Language.GO: ["sh", "-c", f"go build -o {filename}.out {filename} && ./{filename}.out"],
            Language.RUST: ["sh", "-c", f"rustc {filename} -o {filename}.out && ./{filename}.out"],
            Language.JAVA: ["sh", "-c", f"javac {filename} && java {Path(filename).stem}"],
            Language.CSHARP: ["dotnet", "script", filename],
            Language.CPP: ["sh", "-c", f"g++ {filename} -o {filename}.out && ./{filename}.out"],
        }
        return commands.get(language, ["cat", filename])

    
    def _write_seccomp_profile(self, tmpdir: str) -> str:
        """Write seccomp profile to file for runsc."""
        profile = self._generate_seccomp_profile()
        profile_path = Path(tmpdir) / "seccomp.json"
        profile_path.write_text(profile)
        return str(profile_path)

    def _create_import_wrapper(self, request: ExecutionRequest) -> str:
        """Create Python import wrapper that blocks forbidden imports."""
        blocked = request.blocked_imports or [
            "os", "sys", "subprocess", "shutil", "socket", "requests",
            "urllib", "http", "ftplib", "telnetlib", "smtplib",
            "pickle", "marshal", "shelve", "dbm", "sqlite3",
            "importlib", "pkgutil", "runpy", "zipimport",
        ]
        
        allowed = request.allowed_imports or []
        
        wrapper = f'''"""
Import wrapper to block forbidden imports.
Auto-generated for request {request.request_id}
"""
import sys
import builtins

BLOCKED_IMPORTS = {blocked!r}
ALLOWED_IMPORTS = {allowed!r}

original_import = builtins.__import__

def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    # Check if explicitly allowed
    if name in ALLOWED_IMPORTS:
        return original_import(name, globals, locals, fromlist, level)
    
    # Check if blocked
    for blocked_name in BLOCKED_IMPORTS:
        if name == blocked_name or name.startswith(blocked_name + "."):
            raise ImportError(f"Import of '{{name}}' is blocked by security policy")
    
    return original_import(name, globals, locals, fromlist, level)

builtins.__import__ = restricted_import

# Execute user code
exec(open("{filename}").read())
'''
        return wrapper

    async def _run_with_limits(
        self,
        cmd: List[str],
        tmpdir: str,
        request: ExecutionRequest,
        result: ExecutionResult,
    ) -> ExecutionResult:
        """Execute command with resource limits."""
        
        # Prepare environment
        env = os.environ.copy()
        env.update(request.environment)
        
        # Add working directory to env
        env["HOME"] = "/tmp"
        env["TMPDIR"] = "/tmp"
        
        # Start process
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=tmpdir,
            env=env,
            stdin=asyncio.subprocess.PIPE if request.stdin else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        # Track process
        async with self._lock:
            self._active_containers[request.request_id] = proc
        
        result.started_at = datetime.now(timezone.utc)
        
        try:
            # Wait with timeout
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=request.stdin.encode() if request.stdin else None),
                timeout=request.timeout_seconds,
            )
            
            result.completed_at = datetime.now(timezone.utc)
            result.execution_time_ms = int(
                (result.completed_at - result.started_at).total_seconds() * 1000
            )
            
            result.stdout = stdout_bytes.decode('utf-8', errors='replace')
            result.stderr = stderr_bytes.decode('utf-8', errors='replace')
            result.return_code = proc.returncode or 0
            
            # Determine status from return code
            if proc.returncode == 0:
                result.status = ExecutionStatus.COMPLETED
            elif proc.returncode == -9:  # SIGKILL
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
            # Kill process on timeout
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            
            result.completed_at = datetime.now(timezone.utc)
            result.execution_time_ms = int(
                (result.completed_at - result.started_at).total_seconds() * 1000
            )
            result.status = ExecutionStatus.TIMEOUT
            result.error_message = f"Execution timed out after {request.timeout_seconds} seconds"
            result.error_type = "Timeout"
        
        except MemoryError:
            result.status = ExecutionStatus.OOM
            result.error_message = "Out of memory"
            result.error_type = "MemoryError"
        except Exception as e:
            logger.exception(f"Execution error: {e}")
            result.status = ExecutionStatus.ERROR
            result.error_message = str(e)
            result.error_type = type(e).__name__
        
        return result

    def health_check(self) -> bool:
        """Check if gVisor is healthy."""
        try:
            result = subprocess.run(
                [self.config.runsc_path, "version"],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    async def cancel_execution(self, request_id: str) -> bool:
        """Cancel a running execution."""
        async with self._lock:
            proc = self._active_containers.get(request_id)
            if proc:
                try:
                    proc.kill()
                    return True
                except Exception:
                    return False
            return False
    
    def get_active_count(self) -> int:
        with self._lock:
            return len(self._active_containers)


# =============================================================================
# Factory
# =============================================================================


    def _generate_seccomp_profile(self) -> str:
        """Generate a custom seccomp profile for gVisor."""
        import json
        
        profile = {
            "defaultAction": "SCMP_ACT_ERRNO",
            "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_X86", "SCMP_ARCH_X32"],
            "syscalls": [
                {"names": ["read", "write", "open", "close", "stat", "fstat", "lstat", "poll", "lseek", "mmap", 
                           "mprotect", "munmap", "brk", "rt_sigaction", "rt_sigprocmask", "rt_sigreturn", "ioctl",
                           "pread64", "pwrite64", "readv", "writev", "access", "pipe", "select", "sched_yield",
                           "mremap", "msync", "mincore", "madvise", "shmget", "shmat", "shmctl", "dup", "dup2",
                           "pause", "nanosleep", "getitimer", "alarm", "setitimer", "getpid", "sendfile", "socket",
                           "connect", "accept", "sendto", "recvfrom", "sendmsg", "recvmsg", "shutdown", "bind",
                           "listen", "getsockname", "getpeername", "socketpair", "setsockopt", "getsockopt", "clone",
                           "fork", "vfork", "execve", "exit", "wait4", "kill", "uname", "semget", "semop", "semctl",
                           "shmdt", "msgget", "msgsnd", "msgrcv", "msgctl", "fcntl", "flock", "fsync", "fdatasync",
                           "truncate", "ftruncate", "getdents", "getcwd", "chdir", "fchdir", "rename", "mkdir",
                           "rmdir", "creat", "link", "unlink", "symlink", "readlink", "chmod", "fchmod", "chown",
                           "fchown", "lchown", "umask", "gettimeofday", "getrlimit", "getrusage", "sysinfo", "times",
                           "ptrace", "getuid", "syslog", "getgid", "setuid", "setgid", "geteuid", "getegid",
                           "setpgid", "getppid", "getpgrp", "setsid", "setreuid", "setregid", "getgroups",
                           "setgroups", "setresuid", "setresgid", "getpgid", "setfsuid", "setfsgid", "getsid",
                           "capget", "capset", "rt_sigpending", "rt_sigtimedwait", "rt_sigqueueinfo", "rt_sigsuspend",
                           "sigaltstack", "utime", "mknod", "uselib", "personality", "ustat", "statfs", "fstatfs",
                           "sysfs", "getpriority", "setpriority", "sched_setparam", "sched_getparam",
                           "sched_setscheduler", "sched_getscheduler", "sched_get_priority_max", "sched_get_priority_min",
                           "sched_rr_get_interval", "mlock", "munlock", "mlockall", "munlockall", "vhangup",
                           "modify_ldt", "pivot_root", "_sysctl", "prctl", "arch_prctl", "set_tid_address",
                           "set_robust_list", "get_robust_list", "futex", "sched_setaffinity", "sched_getaffinity",
                           "set_thread_area", "io_setup", "io_destroy", "io_getevents", "io_submit", "io_cancel",
                           "get_thread_area", "lookup_dcookie", "epoll_create", "epoll_ctl", "epoll_wait",
                           "remap_file_pages", "set_robust_list", "get_robust_list", "splice", "tee",
                           "sync_file_range", "vmsplice", "move_pages", "utimensat", "epoll_pwait", "signalfd",
                           "timerfd_create", "timerfd_settime", "timerfd_gettime", "accept4", "signalfd4",
                           "epoll_create1", "dup3", "pipe2", "inotify_init1", "preadv", "pwritev",
                           "rt_tgsigqueueinfo", "perf_event_open", "recvmmsg", "fanotify_init", "fanotify_mark",
                           "prlimit64", "name_to_handle_at", "openat", "close"],
                 "action": "SCMP_ACT_ALLOW"}
            ]
        }
        return json.dumps(profile)

def create_gvisor_sandbox(config: Optional[GVisorConfig] = None) -> GVisorSandbox:
    """Create a gVisor sandbox instance."""
    return GVisorSandbox(config)
