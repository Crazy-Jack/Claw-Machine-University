"""Process monitor for tracking running experiments."""

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ProcessStatus(BaseModel):
    """Status of a running process."""

    experiment_id: str = Field(..., description="Experiment ID")
    running: bool = Field(..., description="Whether process is running")
    last_check_time: str = Field(..., description="ISO timestamp of last check")
    pid: int | None = Field(None, description="Process ID")
    uptime_seconds: float | None = Field(None, description="Process uptime in seconds")
    log_tail: str = Field("", description="Last N lines from log file")
    gpu_memory_mb: float | None = Field(None, description="GPU memory usage")
    gpu_utilization: float | None = Field(None, description="GPU utilization %")
    status_message: str = Field("", description="Additional status information")


class ProcessMonitor:
    """Monitor for tracking running experiment processes."""

    def __init__(
        self,
        workspace_path: str = "./autolab_workspace",
        check_interval_seconds: int = 60,
        log_tail_lines: int = 50,
    ) -> None:
        """Initialize process monitor.

        Args:
            workspace_path: Path to workspace.
            check_interval_seconds: Interval between status checks.
            log_tail_lines: Number of log lines to fetch.
        """
        self.workspace_path = Path(workspace_path).expanduser().resolve()
        self.check_interval = check_interval_seconds
        self.log_tail_lines = log_tail_lines

    def check_status(
        self,
        experiment_id: str,
        worker_name: str,
        gpu_id: str,
        pid: int,
        is_remote: bool = False,
        ssh_runner: Any = None,
        local_runner: Any = None,
    ) -> ProcessStatus:
        """Check status of a running experiment.

        Args:
            experiment_id: Experiment ID.
            worker_name: Worker name.
            gpu_id: GPU ID.
            pid: Process ID.
            is_remote: Whether running on remote worker.
            ssh_runner: SSH runner for remote jobs.
            local_runner: Local runner for local jobs.

        Returns:
            ProcessStatus object.
        """
        check_time = datetime.utcnow().isoformat() + "Z"

        # Check if process is running
        if is_remote and ssh_runner:
            proc_info = ssh_runner.check_process(pid)
            log_tail = ssh_runner.read_remote_file_tail(
                self._get_log_path(experiment_id),
                self.log_tail_lines,
            )
            gpu_status = ssh_runner.get_gpu_status(gpu_id)
        elif not is_remote and local_runner:
            proc_info = local_runner.check_process(pid)
            log_tail = local_runner.read_file_tail(
                self._get_log_path(experiment_id),
                self.log_tail_lines,
            )
            gpu_status = local_runner.get_gpu_status(gpu_id)
        else:
            proc_info = {"running": False, "reason": "No runner available"}
            log_tail = ""
            gpu_status = {}

        # Extract GPU info
        gpu_memory = None
        gpu_util = None
        if "memory_used_mb" in gpu_status:
            gpu_memory = gpu_status["memory_used_mb"]
        if "utilization_percent" in gpu_status:
            gpu_util = gpu_status["utilization_percent"]

        # Calculate uptime
        uptime = None
        if "create_time" in proc_info:
            create_time = proc_info["create_time"]
            uptime = time.time() - create_time

        return ProcessStatus(
            experiment_id=experiment_id,
            running=proc_info.get("running", False),
            last_check_time=check_time,
            pid=pid,
            uptime_seconds=uptime,
            log_tail=log_tail,
            gpu_memory_mb=gpu_memory,
            gpu_utilization=gpu_util,
            status_message=proc_info.get("reason", ""),
        )

    def detect_completion(
        self,
        status: ProcessStatus,
        experiment_start_time: str,
        max_runtime_minutes: int | None = None,
    ) -> tuple[bool, str]:
        """Detect if an experiment has completed or failed.

        Args:
            status: Process status from check_status.
            experiment_start_time: ISO timestamp when experiment started.
            max_runtime_minutes: Maximum allowed runtime.

        Returns:
            Tuple of (is_complete, completion_reason).
        """
        # Check if process is not running
        if not status.running:
            # Check log for success indicators
            if self._has_success_indicators(status.log_tail):
                return True, "completed_successfully"

            # Check log for failure indicators
            failure_reason = self._detect_failure_type(status.log_tail)
            if failure_reason:
                return True, f"failed:{failure_reason}"

            # Process stopped without clear indicators
            return True, "stopped_unknown"

        # Check for timeout
        if max_runtime_minutes:
            start_time = datetime.fromisoformat(experiment_start_time.replace("Z", "+00:00"))
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > max_runtime_minutes * 60:
                return True, "timeout"

        return False, "running"

    def _has_success_indicators(self, log_tail: str) -> bool:
        """Check if log shows successful completion.

        Args:
            log_tail: Log tail content.

        Returns:
            True if success indicators found.
        """
        success_indicators = [
            "Training completed",
            "Job finished",
            "Experiment finished",
            "Successfully completed",
            "Done.",
            "All experiments completed",
            "Evaluation finished",
        ]

        log_lower = log_tail.lower()
        for indicator in success_indicators:
            if indicator.lower() in log_lower:
                return True

        return False

    def _detect_failure_type(self, log_tail: str) -> str | None:
        """Detect failure type from log.

        Args:
            log_tail: Log tail content.

        Returns:
            Failure type string or None.
        """
        log_lower = log_tail.lower()

        # OOM
        oom_indicators = ["out of memory", "cuda out of memory", "memory error", "memory allocation failed"]
        if any(ind in log_lower for ind in oom_indicators):
            return "oom"

        # NaN divergence
        nan_indicators = ["nan loss", "nan accuracy", "divergence detected", "gradient became nan"]
        if any(ind in log_lower for ind in nan_indicators):
            return "nan_divergence"

        # Timeout
        timeout_indicators = ["timeout", "timed out", "time limit exceeded"]
        if any(ind in log_lower for ind in timeout_indicators):
            return "timeout"

        # Import error
        import_indicators = ["importerror", "module not found", "no module named"]
        if any(ind in log_lower for ind in import_indicators):
            return "import_error"

        # Syntax error
        syntax_indicators = ["syntaxerror", "invalid syntax"]
        if any(ind in log_lower for ind in syntax_indicators):
            return "syntax_error"

        # Dataset missing
        dataset_indicators = ["file not found", "no such file", "dataset not found", "path does not exist"]
        if any(ind in log_lower for ind in dataset_indicators):
            return "dataset_missing"

        # Runtime exception
        if "error:" in log_lower or "exception:" in log_lower:
            return "runtime_exception"

        return None

    def detect_stall(
        self,
        experiment_id: str,
        last_progress_time: str,
        stall_timeout_minutes: int = 30,
    ) -> bool:
        """Detect if an experiment has stalled (no progress).

        Args:
            experiment_id: Experiment ID.
            last_progress_time: ISO timestamp of last progress.
            stall_timeout_minutes: Timeout before considering stalled.

        Returns:
            True if stalled.
        """
        if not last_progress_time:
            return False

        last_time = datetime.fromisoformat(last_progress_time.replace("Z", "+00:00"))
        elapsed = (datetime.utcnow() - last_time).total_seconds()

        return elapsed > stall_timeout_minutes * 60

    def update_progress_timestamp(self, experiment_id: str) -> None:
        """Update progress timestamp for an experiment.

        Args:
            experiment_id: Experiment ID.
        """
        progress_file = self.workspace_path / "state" / "progress.json"

        try:
            import json

            progress = {}
            if progress_file.exists():
                with open(progress_file) as f:
                    progress = json.load(f)

            progress[experiment_id] = datetime.utcnow().isoformat() + "Z"

            with open(progress_file, "w") as f:
                json.dump(progress, f, indent=2)
        except Exception:
            pass

    def get_progress_timestamp(self, experiment_id: str) -> str | None:
        """Get last progress timestamp for an experiment.

        Args:
            experiment_id: Experiment ID.

        Returns:
            ISO timestamp or None.
        """
        progress_file = self.workspace_path / "state" / "progress.json"

        try:
            import json

            if not progress_file.exists():
                return None

            with open(progress_file) as f:
                progress = json.load(f)

            return progress.get(experiment_id)
        except Exception:
            return None

    def _get_log_path(self, experiment_id: str) -> str:
        """Get log file path for an experiment.

        Args:
            experiment_id: Experiment ID.

        Returns:
            Path to log file.
        """
        log_dir = self.workspace_path / "logs"
        return str(log_dir / f"{experiment_id}.log")
