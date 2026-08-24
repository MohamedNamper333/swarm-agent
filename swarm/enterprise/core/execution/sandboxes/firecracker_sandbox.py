"""
Firecracker MicroVM Sandbox Backend - Secure isolation using Firecracker microVMs.
Provides hardware-level isolation with minimal overhead.
"""

import asyncio
import json
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from ..sandbox import (
    ExecutionRequest, ExecutionResult, ExecutionStatus, Language,
    SandboxBackend
)

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


@dataclass
class FirecrackerConfig:
    """Firecracker sandbox configuration."""
    firecracker_path: str = "firecracker"
    jailer_path: str = "jailer"
    kernel_image: str = "/opt/firecracker/vmlinux.bin"
    rootfs_image: str = "/opt/firecracker/rootfs.ext4"
    kernel_args: str = "console=ttyS0 reboot=k panic=1 pci=off nomodules"
    cpu_count: int = 1
    memory_mb: int = 256
    network_enabled: bool = False
    jailer_cage_path: str = "/run/firecracker"
    kernel_args_extra: str = ""


class FirecrackerSandbox(SandboxBackend):
    """Firecracker MicroVM-based sandbox backend."""

    def __init__(self, config: Optional[FirecrackerConfig] = None):
        self.config = config or FirecrackerConfig()
        self._active_vms: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        
        # Verify firecracker is available
        self._verify_firecracker()
    
    def _verify_firecracker(self) -> None:
        """Verify firecracker binary is available."""
        try:
            result = subprocess.run(
                [self.config.firecracker_path, "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError(f"firecracker not available: {result.stderr}")
            logger.info(f"Firecracker version: {result.stdout.strip()}")
        except FileNotFoundError:
            raise RuntimeError(
                "firecracker not found. Install from: "
                "https://github.com/firecracker-microvm/firecracker/releases"
            )
        except Exception as e:
            raise RuntimeError(f"Firecracker verification failed: {e}")

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute code in Firecracker MicroVM."""
        request_id = request.request_id or f"exec-{uuid.uuid4()}"
        
        result = ExecutionResult(
            request_id=request_id,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        
        # Track active VM
        vm_info = {
            "request_id": request_id,
            "process": None,
            "socket_path": None,
            "started_at": datetime.now(timezone.utc),
        }
        
        async with self._lock:
            self._active_vms[request_id] = vm_info
        
        try:
            with tempfile.TemporaryDirectory(prefix=f"fc-{request_id}-") as tmpdir:
                # Create rootfs overlay
                rootfs_path = await self._prepare_rootfs(tmpdir, request)
                
                # Create kernel args
                kernel_args = self._build_kernel_args(request)
                
                # Create jailer config
                jailer_config = self._create_jailer_config(request_id, tmpdir)
                
                # Create firecracker config
                fc_config = self._create_firecracker_config(request, tmpdir, jailer_config)
                
                # Start Firecracker
                result = await self._run_firecracker(
                    request_id, fc_config, request, result
                )
            
            return result
        
        except Exception as e:
            logger.error(f"Firecracker execution error: {e}")
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
            await self._cleanup_vm(request_id)

    async def _prepare_rootfs(self, tmpdir: str, request: ExecutionRequest) -> str:
        """Prepare rootfs with user code and files using overlayfs (copy-on-write)."""
        # Use overlayfs instead of copying the entire rootfs (FC-6)
        rootfs_path = Path(tmpdir) / "rootfs.ext4"
        
        # Create overlay directories
        lower_dir = Path(tmpdir) / "lower"
        upper_dir = Path(tmpdir) / "upper"
        work_dir = Path(tmpdir) / "work"
        merged_dir = Path(tmpdir) / "merged"
        
        for d in [lower_dir, upper_dir, work_dir, merged_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Mount overlayfs (copy-on-write) instead of shutil.copy2
        try:
            subprocess.run([
                "mount", "-t", "overlay", "overlay",
                "-o", f"lowerdir={self.config.rootfs_image},upperdir={upper_dir},workdir={work_dir}",
                str(merged_dir)
            ], check=True, capture_output=True)
            logger.info(f"Mounted overlayfs for Firecracker: {merged_dir}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Overlayfs mount failed, falling back to copy: {e}")
            # Fallback to copy
            shutil.copy2(self.config.rootfs_image, rootfs_path)
            merged_dir = Path(tmpdir) / "mnt"
            merged_dir.mkdir()
            subprocess.run(["mount", "-o", "loop", str(rootfs_path), str(merged_dir)], 
                          check=True, capture_output=True)
        
        try:
            # Write code file to the overlay
            code_file = self._write_code_file(merged_dir, request)
            
            # Write input files
            for filename, content in request.files.items():
                filepath = merged_dir / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(content)
            
            return str(merged_dir)
        finally:
            # Cleanup will be handled by _cleanup_vm
            pass

    def _write_code_file(self, rootfs: Path, request: ExecutionRequest) -> str:
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
        filepath = Path("/workspace") / filename
        
        # Write to mounted rootfs
        full_path = Path("/mnt") / filename
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(request.code)
        
        return str(filepath)

    def _build_kernel_args(self, request: ExecutionRequest) -> str:
        """Build kernel command line arguments."""
        args = [
            self.config.kernel_args,
            f"panic=1",
            f"init=/sbin/init",
            f"rw",
        ]
        
        if request.network_allowed:
            args.append("ip=dhcp")
        else:
            args.append("ip=off")
        
        if self.config.kernel_args_extra:
            args.append(self.config.kernel_args_extra)
        
        return " ".join(args)

    def _create_jailer_config(self, request_id: str, tmpdir: str) -> Dict[str, Any]:
        """Create jailer configuration with proper cage setup."""
        cage_path = Path(self.config.jailer_cage_path) / request_id
        cage_path.mkdir(parents=True, exist_ok=True)
        
        # Create required subdirectories in cage
        (cage_path / "root").mkdir(exist_ok=True)
        (cage_path / "root" / "dev").mkdir(exist_ok=True)
        (cage_path / "root" / "sys").mkdir(exist_ok=True)
        (cage_path / "root" / "proc").mkdir(exist_ok=True)
        (cage_path / "root" / "tmp").mkdir(exist_ok=True)
        
        return {
            "jailer_binary": self.config.jailer_path,
            "cage_path": str(cage_path),
            "uid": os.getuid(),
            "gid": os.getgid(),
            "netns": f"/var/run/netns/fc-{request_id}" if self.config.network_enabled else None,
        }

    def _create_firecracker_config(
        self, 
        request: ExecutionRequest, 
        tmpdir: str,
        jailer_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create Firecracker configuration JSON."""
        
        # Build drives - use the prepared rootfs path
        drives = [
            {
                "drive_id": "rootfs",
                "path_on_host": f"{tmpdir}/rootfs.ext4",
                "is_root_device": True,
                "is_read_only": False,
            }
        ]
        
        # Network
        network_interfaces = []
        if request.network_allowed:
            network_interfaces.append({
                "iface_id": "eth0",
                "host_dev_name": "tap0",
            })
        
        # Machine config
        config = {
            "boot-source": {
                "kernel_image_path": self.config.kernel_image,
                "boot_args": self._build_kernel_args(request),
            },
            "drives": drives,
            "machine-config": {
                "vcpu_count": self.config.cpu_count,
                "mem_size_mib": self.config.memory_mb,
                "ht_enabled": False,
            },
        }
        
        if request.network_allowed:
            config["network-interfaces"] = network_interfaces
        
        # Add vsock for stdout/stderr capture (FC-5)
        config["vsock"] = {
            "vsock_id": "vsock0",
            "guest_cid": 3,
            "uds_path": f"/tmp/firecracker-{request.request_id}.vsock"
        }
        
        return config

    async def _run_firecracker(
        self,
        request_id: str,
        fc_config: Dict[str, Any],
        request: ExecutionRequest,
        result: ExecutionResult,
    ) -> ExecutionResult:
        """Run Firecracker with the given configuration."""
        
        tmpdir = tempfile.mkdtemp(prefix=f"fc-{request_id}-")
        
        try:
            # Write config
            config_path = Path(tmpdir) / "config.json"
            with open(config_path, "w") as f:
                json.dump(fc_config, f)
            
            # Create socket path
            socket_path = f"/tmp/firecracker-{request_id}.sock"
            
            # Build command
            cmd = [
                self.config.jailer_path,
                "--id", request_id,
                "--cage-path", f"/tmp/fc-cage-{request_id}",
                "--exec-file", self.config.firecracker_path,
                "--uid", str(os.getuid()),
                "--gid", str(os.getgid()),
                "--",  # jailer args end, firecracker args begin
                "--api-sock", socket_path,
                "--config-file", str(config_path),
                "--no-daemon",
            ]
            
            # Start process
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            # Update VM info
            async with self._lock:
                if request_id in self._active_vms:
                    self._active_vms[request_id]["process"] = proc
                    self._active_vms[request_id]["socket_path"] = socket_path
            
            result.started_at = datetime.now(timezone.utc)
            
            # Wait with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=request.timeout_seconds,
                )
                
                result.completed_at = datetime.now(timezone.utc)
                result.execution_time_ms = int(
                    (result.completed_at - result.started_at).total_seconds() * 1000
                )
                
                result.stdout = stdout_bytes.decode('utf-8', errors='replace')
                result.stderr = stderr_bytes.decode('utf-8', errors='replace')
                result.return_code = proc.returncode or 0
                
                if proc.returncode == 0:
                    result.status = ExecutionStatus.COMPLETED
                else:
                    result.status = ExecutionStatus.FAILED
                    result.error_message = f"Firecracker exited with code {proc.returncode}"
                    result.error_type = "FirecrackerError"
                
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                
                result.completed_at = datetime.now(timezone.utc)
                result.execution_time_ms = int(
                    (result.completed_at - result.started_at).total_seconds() * 1000
                )
                result.status = ExecutionStatus.TIMEOUT
                result.error_message = f"Execution timed out after {request.timeout_seconds} seconds"
                result.error_type = "Timeout"
            
        except Exception as e:
            logger.exception(f"Firecracker error: {e}")
            result.status = ExecutionStatus.ERROR
            result.error_message = str(e)
            result.error_type = type(e).__name__
        
        finally:
            # Cleanup
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass
            
            # Unmount overlayfs if used
            try:
                merged_dir = Path(tmpdir) / "merged"
                if merged_dir.exists():
                    subprocess.run(["umount", "-R", str(merged_dir)], capture_output=True)
            except Exception:
                pass
            
            return result


    async def _cleanup_vm(self, request_id: str) -> None:
        """Clean up VM resources including loop devices and tap interfaces."""
        async with self._lock:
            vm_info = self._active_vms.pop(request_id, None)
            if vm_info and vm_info.get("process"):
                try:
                    vm_info["process"].kill()
                except Exception:
                    pass
            
            # Cleanup loop devices (FC-4)
            try:
                # Find and detach loop devices associated with this VM
                result = subprocess.run(
                    ["losetup", "-j", f"/tmp/fc-{request_id}"],
                    capture_output=True, text=True
                )
                if result.returncode == 0 and result.stdout:
                    for line in result.stdout.strip().split("\n"):
                        if line:
                            loop_dev = line.split(":")[0]
                            subprocess.run(["losetup", "-d", loop_dev], capture_output=True)
                            logger.info(f"Detached loop device: {loop_dev}")
            except Exception as e:
                logger.warning(f"Failed to cleanup loop devices: {e}")
            
            # Cleanup tap interfaces (FC-4)
            try:
                tap_name = f"tap-{request_id[:10]}"
                subprocess.run(["ip", "link", "del", tap_name], capture_output=True)
                logger.info(f"Deleted tap interface: {tap_name}")
            except Exception as e:
                logger.warning(f"Failed to cleanup tap interface: {e}")

    def health_check(self) -> bool:
        """Check if Firecracker is healthy."""
        try:
            result = subprocess.run(
                [self.config.firecracker_path, "--version"],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    async def cancel_execution(self, request_id: str) -> bool:
        """Cancel a running execution."""
        async with self._lock:
            vm_info = self._active_vms.get(request_id)
            if vm_info and vm_info.get("process"):
                try:
                    vm_info["process"].kill()
                    return True
                except Exception:
                    return False
            return False
    
    def get_active_count(self) -> int:
        with self._lock:
            return len(self._active_vms)


# =============================================================================
# Factory
# =============================================================================

def create_firecracker_sandbox(config: Optional[FirecrackerConfig] = None) -> FirecrackerSandbox:
    """Create a Firecracker sandbox instance."""
    return FirecrackerSandbox(config)
