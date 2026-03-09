"""Job runner for launching and managing experiments."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from autolab.executor.gpu_scheduler import GPUScheduler, SchedulingDecision
from autolab.executor.local_runner import LocalRunner, LocalExecutionResult
from autolab.executor.process_monitor import ProcessMonitor, ProcessStatus
from autolab.executor.ssh_runner import SSHExecutionResult, SSHRunner
from autolab.executor.worker_registry import WorkerRegistry
from autolab.schemas.experiment import Experiment


class JobLaunchResult(BaseModel):
    """Result of launching a job."""

    success: bool = Field(..., description="Whether launch succeeded")
    experiment_id: str = Field(..., description="Experiment ID")
    worker_name: str | None = Field(None, description="Worker name")
    gpu_id: str | None = Field(None, description="GPU ID")
    pid: int | None = Field(None, description="Process ID")
    log_path: str | None = Field(None, description="Log file path")
    error_message: str = Field("", description="Error message if failed")
    launch_time: str = Field(..., description="ISO timestamp of launch")


class JobRunner:
    """Runner for managing experiment jobs on workers."""

    def __init__(
        self,
        worker_registry: WorkerRegistry,
        workspace_path: str = "./autolab_workspace",
    ) -> None:
        """Initialize job runner.

        Args:
            worker_registry: Worker registry.
            workspace_path: Path to workspace.
        """
        self.registry = worker_registry
        self.scheduler = GPUScheduler(worker_registry)
        self.workspace_path = Path(workspace_path).expanduser().resolve()
        self.monitor = ProcessMonitor(str(self.workspace_path))

        # Cache of runners
        self.ssh_runners: dict[str, SSHRunner] = {}
        self.local_runner = LocalRunner()

    def launch_experiment(self, experiment: Experiment) -> JobLaunchResult:
        """Launch an experiment.

        Args:
            experiment: Experiment to launch.

        Returns:
            JobLaunchResult object.
        """
        launch_time = datetime.utcnow().isoformat() + "Z"

        # Check if dependencies are satisfied
        if experiment.dependencies:
            # This should be handled by the controller, but check anyway
            return JobLaunchResult(
                success=False,
                experiment_id=experiment.id,
                error_message=f"Dependencies not satisfied: {experiment.dependencies}",
                launch_time=launch_time,
            )

        # Select worker
        decision = self._select_worker(experiment)
        if not decision:
            return JobLaunchResult(
                success=False,
                experiment_id=experiment.id,
                error_message="No suitable worker available",
                launch_time=launch_time,
            )

        # Get runner
        runner = self._get_runner(decision.worker_name)
        if not runner:
            return JobLaunchResult(
                success=False,
                experiment_id=experiment.id,
                error_message=f"Failed to get runner for worker {decision.worker_name}",
                launch_time=launch_time,
            )

        # Prepare log path
        log_path = self._prepare_log_path(experiment.id)

        # Prepare environment
        environment = self._prepare_environment(experiment)

        # Prepare command
        command = self._prepare_command(experiment)

        # Determine if remote
        worker = self.registry.get(decision.worker_name)
        is_remote = worker.is_local if worker else False

        # Launch job
        if is_remote:
            result: SSHExecutionResult | LocalExecutionResult = runner.launch_detached_job(
                command=command,
                working_dir=experiment.working_dir,
                log_path=log_path if is_remote else None,
                environment=environment,
                gpu_id=decision.gpu_id,
            )
        else:
            result = self.local_runner.launch_detached_job(
                command=command,
                working_dir=experiment.working_dir,
                log_path=log_path,
                environment=environment,
                gpu_id=decision.gpu_id,
            )

        if not result.success or result.pid is None:
            return JobLaunchResult(
                success=False,
                experiment_id=experiment.id,
                error_message=result.stderr or "Launch failed",
                launch_time=launch_time,
            )

        # Update worker job count
        self.registry.increment_job_count(decision.worker_name)

        return JobLaunchResult(
            success=True,
            experiment_id=experiment.id,
            worker_name=decision.worker_name,
            gpu_id=decision.gpu_id,
            pid=result.pid,
            log_path=log_path,
            launch_time=launch_time,
        )

    def check_experiment_status(self, experiment: Experiment) -> ProcessStatus:
        """Check status of a running experiment.

        Args:
            experiment: Experiment to check.

        Returns:
            ProcessStatus object.
        """
        if experiment.status != "running":
            return ProcessStatus(
                experiment_id=experiment.id,
                running=False,
                last_check_time=datetime.utcnow().isoformat() + "Z",
                status_message=f"Experiment not running (status: {experiment.status})",
            )

        if not experiment.worker_name or not experiment.pid:
            return ProcessStatus(
                experiment_id=experiment.id,
                running=False,
                last_check_time=datetime.utcnow().isoformat() + "Z",
                status_message="Missing worker or PID information",
            )

        # Get worker
        worker = self.registry.get(experiment.worker_name)
        if not worker:
            return ProcessStatus(
                experiment_id=experiment.id,
                running=False,
                last_check_time=datetime.utcnow().isoformat() + "Z",
                status_message=f"Worker not found: {experiment.worker_name}",
            )

        # Get runner
        runner = self._get_runner(experiment.worker_name)
        if not runner:
            return ProcessStatus(
                experiment_id=experiment.id,
                running=False,
                last_check_time=datetime.utcnow().isoformat() + "Z",
                status_message=f"Failed to get runner for worker {experiment.worker_name}",
            )

        is_remote = worker.is_local if worker else False
        gpu_id = experiment.gpu_id or "0"

        # Check status
        status = self.monitor.check_status(
            experiment_id=experiment.id,
            worker_name=experiment.worker_name,
            gpu_id=gpu_id,
            pid=experiment.pid,
            is_remote=not is_remote,
            ssh_runner=runner if not is_remote else None,
            local_runner=self.local_runner if is_remote else None,
        )

        return status

    def stop_experiment(self, experiment: Experiment, force: bool = False) -> bool:
        """Stop a running experiment.

        Args:
            experiment: Experiment to stop.
            force: Whether to force kill.

        Returns:
            True if successful.
        """
        if experiment.status != "running":
            return False

        if not experiment.worker_name or not experiment.pid:
            return False

        # Get runner
        runner = self._get_runner(experiment.worker_name)
        if not runner:
            return False

        # Kill process
        if isinstance(runner, SSHRunner):
            success = runner.kill_process(experiment.pid, force)
        else:
            success = self.local_runner.kill_process(experiment.pid, force)

        if success and experiment.worker_name:
            self.registry.decrement_job_count(experiment.worker_name)

        return success

    def _select_worker(self, experiment: Experiment) -> SchedulingDecision | None:
        """Select a worker for an experiment.

        Args:
            experiment: Experiment to schedule.

        Returns:
            SchedulingDecision or None.
        """
        # Get memory requirement
        required_memory = experiment.resource_request.get("gpu_memory_gb")
        min_memory = experiment.resource_request.get("min_gpu_memory_gb", 0.0)

        # Get GPU type preference
        preferred_type = experiment.resource_request.get("gpu_type")

        # Get affinity worker (from parent experiment)
        affinity_worker = None
        if experiment.parent_experiment_id:
            # Would need to load parent experiment to get its worker
            pass

        return self.scheduler.select_worker_for_experiment(
            required_memory_gb=required_memory,
            preferred_gpu_type=preferred_type,
            min_memory_gb=min_memory,
            affinity_worker=affinity_worker,
        )

    def _get_runner(self, worker_name: str) -> SSHRunner | LocalRunner | None:
        """Get runner for a worker.

        Args:
            worker_name: Worker name.

        Returns:
            Runner instance or None.
        """
        worker = self.registry.get(worker_name)
        if not worker:
            return None

        # Check if local
        if worker.is_local:
            return self.local_runner

        # Get or create SSH runner
        if worker_name not in self.ssh_runners:
            self.ssh_runners[worker_name] = SSHRunner(
                host=worker.host,
                user=worker.user,
                ssh_key_path=worker.ssh_key,
            )

        return self.ssh_runners[worker_name]

    def _prepare_log_path(self, experiment_id: str) -> str:
        """Prepare log file path.

        Args:
            experiment_id: Experiment ID.

        Returns:
            Log file path.
        """
        log_dir = self.workspace_path / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return str(log_dir / f"{experiment_id}.log")

    def _prepare_environment(self, experiment: Experiment) -> dict[str, str]:
        """Prepare environment variables.

        Args:
            experiment: Experiment.

        Returns:
            Dictionary of environment variables.
        """
        env = {}

        # Add experiment-specific env vars
        if "environment" in experiment.resource_request:
            env.update(experiment.resource_request["environment"])

        return env

    def _prepare_command(self, experiment: Experiment) -> str:
        """Prepare launch command.

        Args:
            experiment: Experiment.

        Returns:
            Command string.
        """
        # Use launch_command from experiment
        if experiment.launch_command:
            return " ".join(experiment.launch_command)

        # Default command: train with config
        config_path = experiment.config_path
        return f"python train.py --config {config_path}"

    def cleanup(self) -> None:
        """Clean up resources."""
        # Disconnect all SSH runners
        for runner in self.ssh_runners.values():
            runner.disconnect()
        self.ssh_runners.clear()

        # Clean up local runner
        self.local_runner.cleanup()


from pydantic import BaseModel, Field
