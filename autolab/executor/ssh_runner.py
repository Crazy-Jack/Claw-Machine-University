"""SSH runner for executing jobs on remote GPU workers."""

import os
import subprocess
import time
from pathlib import Path
from typing import Any

import paramiko
from pydantic import BaseModel, Field


class SSHExecutionResult(BaseModel):
    """Result of SSH execution."""

    success: bool = Field(..., description="Whether execution succeeded")
    stdout: str = Field(..., description="Standard output")
    stderr: str = Field(..., description="Standard error")
    exit_code: int | None = Field(None, description="Exit code")
    remote_pid: int | None = Field(None, description="Process ID on remote host")


class SSHRunner:
    """Runner for executing commands on remote SSH workers."""

    def __init__(
        self,
        host: str,
        user: str,
        ssh_key_path: str = "~/.ssh/id_ed25519",
        timeout: int = 30,
    ) -> None:
        """Initialize SSH runner.

        Args:
            host: Remote host address.
            user: Username for SSH connection.
            ssh_key_path: Path to SSH private key.
            timeout: Connection timeout in seconds.
        """
        self.host = host
        self.user = user
        self.ssh_key_path = Path(ssh_key_path).expanduser().resolve()
        self.timeout = timeout
        self.client: paramiko.SSHClient | None = None

    def connect(self) -> bool:
        """Establish SSH connection.

        Returns:
            True if connection successful.
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.client.connect(
                hostname=self.host,
                username=self.user,
                key_filename=str(self.ssh_key_path),
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False,
            )
            return True
        except Exception as e:
            print(f"SSH connection failed: {e}")
            return False

    def disconnect(self) -> None:
        """Close SSH connection."""
        if self.client:
            self.client.close()
            self.client = None

    def run_command(
        self,
        command: str,
        timeout: int = 300,
        environment: dict[str, str] | None = None,
    ) -> SSHExecutionResult:
        """Run a command on remote host.

        Args:
            command: Command to execute.
            timeout: Command timeout in seconds.
            environment: Environment variables to set.

        Returns:
            SSHExecutionResult object.
        """
        if not self.client or not self._is_connected():
            if not self.connect():
                return SSHExecutionResult(
                    success=False,
                    stdout="",
                    stderr="Failed to establish SSH connection",
                    exit_code=-1,
                )

        try:
            # Build command with environment variables
            if environment:
                env_str = " ".join(f"{k}={v}" for k, v in environment.items())
                full_command = f"{env_str} {command}"
            else:
                full_command = command

            # Execute command
            stdin, stdout, stderr = self.client.exec_command(
                full_command,
                timeout=timeout,
                get_pty=False,
            )

            # Read output
            stdout_str = stdout.read().decode("utf-8", errors="replace")
            stderr_str = stderr.read().decode("utf-8", errors="replace")
            exit_code = stdout.channel.recv_exit_status()

            return SSHExecutionResult(
                success=exit_code == 0,
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=exit_code,
            )
        except Exception as e:
            return SSHExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
            )

    def launch_detached_job(
        self,
        command: str,
        working_dir: str = ".",
        log_path: str | None = None,
        environment: dict[str, str] | None = None,
        gpu_id: str = "0",
    ) -> SSHExecutionResult:
        """Launch a detached job on remote host.

        Args:
            command: Command to execute.
            working_dir: Working directory for the job.
            log_path: Path to redirect stdout.
            environment: Environment variables.
            gpu_id: GPU ID to use.

        Returns:
            SSHExecutionResult with remote PID.
        """
        # Build environment
        env_vars = {
            "CUDA_VISIBLE_DEVICES": gpu_id,
            "PYTHONUNBUFFERED": "1",
        }
        if environment:
            env_vars.update(environment)

        env_str = " ".join(f"{k}={v}" for k, v in env_vars.items())

        # Build command with nohup and background execution
        if log_path:
            full_command = f"cd {working_dir} && {env_str} nohup {command} > {log_path} 2>&1 & echo $!"
        else:
            full_command = f"cd {working_dir} && {env_str} nohup {command} > /dev/null 2>&1 & echo $!"

        result = self.run_command(full_command, timeout=30)

        if result.success and result.stdout:
            try:
                remote_pid = int(result.stdout.strip())
                result.remote_pid = remote_pid
            except ValueError:
                pass

        return result

    def check_process(
        self,
        pid: int,
    ) -> dict[str, Any]:
        """Check if a process is still running.

        Args:
            pid: Process ID to check.

        Returns:
            Dictionary with process information.
        """
        result = self.run_command(f"ps -p {pid} -o pid,stat,etime,cmd", timeout=10)

        if not result.success:
            return {"running": False, "reason": "Process not found"}

        lines = result.stdout.strip().split("\n")
        if len(lines) < 2:
            return {"running": False, "reason": "Process not found"}

        # Parse process info
        parts = lines[1].split(None, 3)
        return {
            "running": True,
            "pid": int(parts[0]),
            "status": parts[1],
            "elapsed_time": parts[2],
            "command": parts[3] if len(parts) > 3 else "",
        }

    def kill_process(self, pid: int, force: bool = False) -> bool:
        """Kill a process.

        Args:
            pid: Process ID to kill.
            force: Whether to force kill (SIGKILL).

        Returns:
            True if successful.
        """
        signal = "-9" if force else "-15"
        result = self.run_command(f"kill {signal} {pid}", timeout=10)
        return result.success

    def read_remote_file(
        self,
        file_path: str,
    ) -> str:
        """Read a remote file.

        Args:
            file_path: Path to remote file.

        Returns:
            File content.
        """
        if not self.client or not self._is_connected():
            if not self.connect():
                return ""

        try:
            sftp = self.client.open_sftp()
            with sftp.file(file_path, "r") as f:
                return f.read().decode("utf-8", errors="replace")
        except Exception as e:
            return f"Error reading file: {e}"
        finally:
            try:
                sftp.close()
            except Exception:
                pass

    def read_remote_file_tail(
        self,
        file_path: str,
        lines: int = 100,
    ) -> str:
        """Read last N lines of a remote file.

        Args:
            file_path: Path to remote file.
            lines: Number of lines to read.

        Returns:
            File content tail.
        """
        command = f"tail -n {lines} {file_path}"
        result = self.run_command(command, timeout=30)
        return result.stdout

    def get_gpu_status(self, gpu_id: str = "0") -> dict[str, Any]:
        """Get GPU status using nvidia-smi.

        Args:
            gpu_id: GPU ID to query.

        Returns:
            Dictionary with GPU information.
        """
        command = f"nvidia-smi --id={gpu_id} --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits"
        result = self.run_command(command, timeout=10)

        if not result.success:
            return {"error": result.stderr}

        try:
            parts = result.stdout.strip().split(",")
            return {
                "gpu_id": gpu_id,
                "utilization_percent": int(parts[0].strip()),
                "memory_used_mb": int(parts[1].strip()),
                "memory_total_mb": int(parts[2].strip()),
                "temperature_c": int(parts[3].strip()),
            }
        except Exception as e:
            return {"error": f"Failed to parse GPU status: {e}"}

    def get_disk_usage(self, path: str = ".") -> dict[str, Any]:
        """Get disk usage.

        Args:
            path: Path to check.

        Returns:
            Dictionary with disk usage information.
        """
        command = f"df -h {path} | tail -1"
        result = self.run_command(command, timeout=10)

        if not result.success:
            return {"error": result.stderr}

        try:
            parts = result.stdout.split()
            return {
                "total": parts[1],
                "used": parts[2],
                "available": parts[3],
                "percent_used": parts[4],
            }
        except Exception:
            return {"error": "Failed to parse disk usage"}

    def _is_connected(self) -> bool:
        """Check if SSH connection is still active.

        Returns:
            True if connected.
        """
        if not self.client:
            return False

        try:
            transport = self.client.get_transport() if self.client else None
            return transport is not None and transport.is_active()
        except Exception:
            return False
