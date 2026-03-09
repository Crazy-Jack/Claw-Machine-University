"""Local runner for executing jobs on local machine."""

import os
import subprocess
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class LocalExecutionResult(BaseModel):
    """Result of local execution."""

    success: bool = Field(..., description="Whether execution succeeded")
    stdout: str = Field(..., description="Standard output")
    stderr: str = Field(..., description="Standard error")
    exit_code: int | None = Field(None, description="Exit code")
    pid: int | None = Field(None, description="Process ID")


class LocalRunner:
    """Runner for executing commands locally."""

    def __init__(self) -> None:
        """Initialize local runner."""
        self.processes: dict[int, subprocess.Popen] = {}

    def run_command(
        self,
        command: str,
        timeout: int = 300,
        working_dir: str = ".",
        environment: dict[str, str] | None = None,
    ) -> LocalExecutionResult:
        """Run a command locally.

        Args:
            command: Command to execute.
            timeout: Command timeout in seconds.
            working_dir: Working directory.
            environment: Environment variables.

        Returns:
            LocalExecutionResult object.
        """
        try:
            env = os.environ.copy()
            if environment:
                env.update(environment)

            result = subprocess.run(
                command,
                shell=True,
                timeout=timeout,
                cwd=working_dir,
                capture_output=True,
                text=True,
                env=env,
            )

            return LocalExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return LocalExecutionResult(
                success=False,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                exit_code=-1,
            )
        except Exception as e:
            return LocalExecutionResult(
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
    ) -> LocalExecutionResult:
        """Launch a detached job locally.

        Args:
            command: Command to execute.
            working_dir: Working directory for the job.
            log_path: Path to redirect stdout.
            environment: Environment variables.
            gpu_id: GPU ID to use.

        Returns:
            LocalExecutionResult with PID.
        """
        try:
            # Build environment
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = gpu_id
            env["PYTHONUNBUFFERED"] = "1"
            if environment:
                env.update(environment)

            # Prepare command
            if log_path:
                # Redirect to log file
                with open(log_path, "w") as log_file:
                    process = subprocess.Popen(
                        command,
                        shell=True,
                        cwd=working_dir,
                        env=env,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        preexec_fn=os.setsid,  # Create new process group
                    )
            else:
                # No log file
                process = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=working_dir,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setsid,
                )

            # Store process
            self.processes[process.pid] = process

            return LocalExecutionResult(
                success=True,
                stdout=f"Started with PID: {process.pid}",
                stderr="",
                exit_code=0,
                pid=process.pid,
            )
        except Exception as e:
            return LocalExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
            )

    def check_process(self, pid: int) -> dict[str, Any]:
        """Check if a process is still running.

        Args:
            pid: Process ID to check.

        Returns:
            Dictionary with process information.
        """
        try:
            # Check if process exists
            os.kill(pid, 0)
        except OSError:
            return {"running": False, "reason": "Process not found"}

        # Get process info
        try:
            import psutil

            proc = psutil.Process(pid)
            return {
                "running": True,
                "pid": pid,
                "status": proc.status(),
                "create_time": proc.create_time(),
                "cpu_percent": proc.cpu_percent(),
                "memory_mb": proc.memory_info().rss / 1024 / 1024,
                "command": " ".join(proc.cmdline()),
            }
        except ImportError:
            # Fallback without psutil
            return {"running": True, "pid": pid}
        except Exception:
            return {"running": False, "reason": "Error getting process info"}

    def kill_process(self, pid: int, force: bool = False) -> bool:
        """Kill a process.

        Args:
            pid: Process ID to kill.
            force: Whether to force kill (SIGKILL).

        Returns:
            True if successful.
        """
        try:
            if force:
                os.kill(pid, signal.SIGKILL)
            else:
                # Kill entire process group
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                time.sleep(2)
                try:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except OSError:
                    pass

            if pid in self.processes:
                del self.processes[pid]

            return True
        except Exception:
            return False

    def read_file_tail(self, file_path: str, lines: int = 100) -> str:
        """Read last N lines of a file.

        Args:
            file_path: Path to file.
            lines: Number of lines to read.

        Returns:
            File content tail.
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return ""

            with open(path, "r", errors="replace") as f:
                all_lines = f.readlines()

            return "".join(all_lines[-lines:])
        except Exception as e:
            return f"Error reading file: {e}"

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

    def cleanup(self) -> None:
        """Clean up all tracked processes."""
        for pid in list(self.processes.keys()):
            try:
                self.kill_process(pid, force=True)
            except Exception:
                pass
