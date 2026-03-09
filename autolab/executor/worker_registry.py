"""Worker registry for managing GPU workers."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from autolab.schemas.worker import GPU, Worker, WorkerStatus


class WorkerRegistry:
    """Registry for managing GPU workers."""

    def __init__(self, config_path: str = "./autolab/configs/gpu.yaml") -> None:
        """Initialize worker registry.

        Args:
            config_path: Path to GPU configuration file.
        """
        self.config_path = Path(config_path).expanduser().resolve()
        self.workers: dict[str, Worker] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load worker configuration from file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"GPU config not found: {self.config_path}")

        with open(self.config_path) as f:
            config = json.load(f) if self.config_path.suffix == ".json" else self._load_yaml(f)

        self.workers.clear()
        for worker_data in config.get("workers", []):
            worker = Worker(**worker_data)
            self.workers[worker.name] = worker

    def _load_yaml(self, file_obj: Any) -> dict:
        """Load YAML file.

        Args:
            file_obj: File object.

        Returns:
            Dictionary with YAML content.
        """
        import yaml

        return yaml.safe_load(file_obj)

    def get_all(self) -> dict[str, Worker]:
        """Get all workers.

        Returns:
            Dictionary of all workers.
        """
        return self.workers.copy()

    def get_enabled(self) -> dict[str, Worker]:
        """Get enabled workers.

        Returns:
            Dictionary of enabled workers.
        """
        return {name: w for name, w in self.workers.items() if w.enabled}

    def get_online(self) -> dict[str, Worker]:
        """Get online workers.

        Returns:
            Dictionary of online workers.
        """
        return {
            name: w for name, w in self.workers.items()
            if w.enabled and w.status == WorkerStatus.ONLINE
        }

    def get(self, worker_name: str) -> Worker | None:
        """Get a specific worker.

        Args:
            worker_name: Name of worker.

        Returns:
            Worker object or None.
        """
        return self.workers.get(worker_name)

    def get_available_gpus(self) -> dict[str, GPU]:
        """Get all available GPUs.

        Returns:
            Dictionary mapping "worker_name:gpu_id" to GPU objects.
        """
        available = {}

        for worker_name, worker in self.get_online().items():
            # Calculate available GPUs based on current jobs
            for gpu in worker.gpus:
                if worker.current_jobs < worker.max_concurrent_jobs:
                    available[f"{worker_name}:{gpu.id}"] = gpu

        return available

    def update_status(
        self,
        worker_name: str,
        status: WorkerStatus,
        last_heartbeat: str | None = None,
    ) -> None:
        """Update worker status.

        Args:
            worker_name: Name of worker.
            status: New status.
            last_heartbeat: Optional heartbeat timestamp.
        """
        if worker_name not in self.workers:
            return

        worker = self.workers[worker_name]
        worker.status = status

        if last_heartbeat:
            worker.last_heartbeat = last_heartbeat

    def increment_job_count(self, worker_name: str) -> bool:
        """Increment job count for a worker.

        Args:
            worker_name: Name of worker.

        Returns:
            True if successful, False if max concurrent reached.
        """
        if worker_name not in self.workers:
            return False

        worker = self.workers[worker_name]

        if worker.current_jobs >= worker.max_concurrent_jobs:
            return False

        worker.current_jobs += 1
        return True

    def decrement_job_count(self, worker_name: str) -> None:
        """Decrement job count for a worker.

        Args:
            worker_name: Name of worker.
        """
        if worker_name not in self.workers:
            return

        worker = self.workers[worker_name]
        if worker.current_jobs > 0:
            worker.current_jobs -= 1

    def check_heartbeats(self, timeout_seconds: int = 600) -> list[str]:
        """Check worker heartbeats and mark stale workers as offline.

        Args:
            timeout_seconds: Timeout in seconds before marking as offline.

        Returns:
            List of worker names that went offline.
        """
        now = datetime.utcnow()
        offline_workers = []

        for worker_name, worker in self.workers.items():
            if worker.last_heartbeat is None:
                continue

            heartbeat_time = datetime.fromisoformat(worker.last_heartbeat.replace("Z", "+00:00"))
            delta = (now - heartbeat_time).total_seconds()

            if delta > timeout_seconds:
                worker.status = WorkerStatus.OFFLINE
                offline_workers.append(worker_name)

        return offline_workers

    def get_worker_for_gpu(self, gpu_spec: str) -> Worker | None:
        """Get worker for a GPU specification.

        Args:
            gpu_spec: GPU spec in format "worker_name:gpu_id" or "gpu_id".

        Returns:
            Worker object or None.
        """
        if ":" in gpu_spec:
            worker_name, _ = gpu_spec.split(":", 1)
            return self.get(worker_name)

        # Search for GPU by ID
        for worker in self.workers.values():
            for gpu in worker.gpus:
                if gpu.id == gpu_spec:
                    return worker

        return None

    def get_total_gpu_count(self) -> int:
        """Get total number of GPUs across all enabled workers.

        Returns:
            Total GPU count.
        """
        count = 0
        for worker in self.get_enabled().values():
            count += len(worker.gpus)
        return count

    def get_available_gpu_count(self) -> int:
        """Get number of available GPUs.

        Returns:
            Available GPU count.
        """
        return len(self.get_available_gpus())

    def get_worker_summary(self) -> dict[str, Any]:
        """Get summary of worker status.

        Returns:
            Dictionary with summary statistics.
        """
        enabled = self.get_enabled()
        online = self.get_online()

        total_gpus = sum(len(w.gpus) for w in enabled.values())
        total_jobs = sum(w.current_jobs for w in enabled.values())

        return {
            "total_workers": len(self.workers),
            "enabled_workers": len(enabled),
            "online_workers": len(online),
            "total_gpus": total_gpus,
            "available_gpus": self.get_available_gpu_count(),
            "running_jobs": total_jobs,
        }
