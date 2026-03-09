"""GPU scheduler for assigning experiments to available workers."""

from typing import Any

from autolab.executor.worker_registry import WorkerRegistry
from autolab.schemas.worker import GPU


class SchedulingDecision(BaseModel):
    """Decision for scheduling an experiment."""

    worker_name: str = Field(..., description="Selected worker name")
    gpu_id: str = Field(..., description="Selected GPU ID")
    gpu: GPU = Field(..., description="GPU object")
    score: float = Field(..., description="Scheduling score")
    rationale: str = Field(..., description="Reasoning for selection")


class GPUScheduler:
    """Scheduler for assigning experiments to GPU workers."""

    def __init__(self, worker_registry: WorkerRegistry) -> None:
        """Initialize GPU scheduler.

        Args:
            worker_registry: Worker registry instance.
        """
        self.registry = worker_registry

    def select_worker_for_experiment(
        self,
        required_memory_gb: float | None = None,
        preferred_gpu_type: str | None = None,
        min_memory_gb: float = 0.0,
        affinity_worker: str | None = None,
    ) -> SchedulingDecision | None:
        """Select best worker for an experiment.

        Args:
            required_memory_gb: Required GPU memory in GB.
            preferred_gpu_type: Preferred GPU type.
            min_memory_gb: Minimum acceptable GPU memory.
            affinity_worker: Worker with affinity (e.g., same as previous job).

        Returns:
            SchedulingDecision or None if no suitable worker.
        """
        available_gpus = self.registry.get_available_gpus()

        if not available_gpus:
            return None

        # Score each available GPU
        scored = []
        for gpu_spec, gpu in available_gpus.items():
            worker_name, gpu_id = gpu_spec.split(":", 1)
            score = self._score_gpu(
                worker_name,
                gpu,
                required_memory_gb,
                preferred_gpu_type,
                min_memory_gb,
                affinity_worker,
            )

            if score is not None:
                scored.append(
                    SchedulingDecision(
                        worker_name=worker_name,
                        gpu_id=gpu_id,
                        gpu=gpu,
                        score=score,
                        rationale=self._get_rationale(worker_name, gpu, score),
                    )
                )

        if not scored:
            return None

        # Sort by score (descending)
        scored.sort(key=lambda x: x.score, reverse=True)

        return scored[0]

    def _score_gpu(
        self,
        worker_name: str,
        gpu: GPU,
        required_memory_gb: float | None,
        preferred_gpu_type: str | None,
        min_memory_gb: float,
        affinity_worker: str | None,
    ) -> float | None:
        """Score a GPU for scheduling.

        Args:
            worker_name: Worker name.
            gpu: GPU object.
            required_memory_gb: Required memory.
            preferred_gpu_type: Preferred GPU type.
            min_memory_gb: Minimum memory.
            affinity_worker: Worker with affinity.

        Returns:
            Score or None if not suitable.
        """
        # Check minimum memory requirement
        if gpu.memory_gb < min_memory_gb:
            return None

        # Check required memory
        if required_memory_gb and gpu.memory_gb < required_memory_gb:
            return None

        score = 0.0

        # Affinity bonus
        if affinity_worker and worker_name == affinity_worker:
            score += 100.0

        # GPU type preference
        if preferred_gpu_type:
            if preferred_gpu_type.lower() in gpu.type.lower():
                score += 50.0

        # Memory score (prefer appropriate size)
        if required_memory_gb:
            # Bonus for having enough but not too much extra
            ratio = gpu.memory_gb / required_memory_gb
            if ratio >= 1.0 and ratio <= 1.5:
                score += 20.0
            elif ratio <= 2.0:
                score += 10.0
        else:
            # Without requirements, prefer smaller GPUs (leave larger for others)
            score -= gpu.memory_gb * 0.1

        # Prefer workers with fewer jobs (load balancing)
        worker = self.registry.get(worker_name)
        if worker:
            load_ratio = worker.current_jobs / worker.max_concurrent_jobs
            score -= load_ratio * 10.0

        return score

    def _get_rationale(self, worker_name: str, gpu: GPU, score: float) -> str:
        """Generate rationale for scheduling decision.

        Args:
            worker_name: Worker name.
            gpu: GPU object.
            score: Calculated score.

        Returns:
            Rationale string.
        """
        parts = [
            f"Selected {gpu.type} ({gpu.memory_gb}GB) on {worker_name}",
        ]

        if score > 100:
            parts.append("with worker affinity")
        elif score > 50:
            parts.append("matching GPU type preference")
        elif score > 0:
            parts.append("with suitable memory")

        return " ".join(parts)

    def can_schedule_now(
        self,
        required_memory_gb: float | None = None,
        min_memory_gb: float = 0.0,
    ) -> bool:
        """Check if any worker can schedule an experiment now.

        Args:
            required_memory_gb: Required GPU memory.
            min_memory_gb: Minimum memory.

        Returns:
            True if scheduling is possible.
        """
        decision = self.select_worker_for_experiment(
            required_memory_gb=required_memory_gb,
            min_memory_gb=min_memory_gb,
        )
        return decision is not None

    def estimate_wait_time(
        self,
        required_memory_gb: float | None = None,
        min_memory_gb: float = 0.0,
    ) -> dict[str, Any]:
        """Estimate wait time for scheduling.

        Args:
            required_memory_gb: Required GPU memory.
            min_memory_gb: Minimum memory.

        Returns:
            Dictionary with wait time estimate.
        """
        available = self.registry.get_available_gpus()
        total_gpus = self.registry.get_total_gpu_count()

        if available:
            return {
                "can_schedule_now": True,
                "wait_minutes": 0,
                "available_gpus": len(available),
            }

        # Estimate based on average job duration
        # This is a rough estimate; in practice, track actual job durations
        avg_job_minutes = 60  # Default estimate

        running_jobs = sum(w.current_jobs for w in self.registry.get_enabled().values())

        return {
            "can_schedule_now": False,
            "wait_minutes": running_jobs * avg_job_minutes / total_gpus,
            "running_jobs": running_jobs,
            "total_gpus": total_gpus,
        }

    def get_resource_summary(self) -> dict[str, Any]:
        """Get summary of available resources.

        Returns:
            Dictionary with resource summary.
        """
        available_gpus = self.registry.get_available_gpus()
        enabled_workers = self.registry.get_enabled()

        gpu_types = {}
        for gpu in available_gpus.values():
            gpu_types[gpu.type] = gpu_types.get(gpu.type, 0) + 1

        total_memory = sum(gpu.memory_gb for gpu in available_gpus.values())

        return {
            "available_gpus": len(available_gpus),
            "gpu_types": gpu_types,
            "total_memory_gb": total_memory,
            "workers": {
                name: {
                    "gpus": len([g for g in worker.gpus if f"{name}:{g.id}" in available_gpus]),
                    "current_jobs": worker.current_jobs,
                    "max_concurrent": worker.max_concurrent_jobs,
                }
                for name, worker in enabled_workers.items()
            },
        }


from pydantic import BaseModel, Field
