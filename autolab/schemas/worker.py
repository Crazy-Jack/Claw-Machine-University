"""Pydantic schema for GPU workers."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GPUInfo(BaseModel):
    """Information about a single GPU."""

    id: str = Field(..., description="GPU ID (e.g., '0', '1')")
    type: str = Field(..., description="GPU type (e.g., 'A100', 'H100')")
    memory_gb: int = Field(..., ge=0, description="GPU memory in GB")


class Worker(BaseModel):
    """Represents a GPU worker (remote or local)."""

    name: str = Field(..., description="Unique worker name")
    host: str = Field(..., description="Worker hostname or IP")
    user: str = Field(..., description="SSH username for remote workers")
    ssh_key: str = Field(..., description="Path to SSH private key")
    gpus: list[GPUInfo] = Field(..., description="List of GPUs on this worker")
    enabled: bool = Field(True, description="Whether this worker is enabled")
    is_local: bool = Field(False, description="Whether this is a local worker")
    max_concurrent_jobs: int = Field(1, ge=1, description="Max concurrent jobs per GPU")
    current_jobs: int = Field(0, ge=0, description="Currently running jobs")
    last_heartbeat: str | None = Field(None, description="ISO timestamp of last heartbeat")
    status: Literal["online", "offline", "unreachable"] = Field("unknown", description="Worker status")
    metadata: dict = Field(default_factory=dict, description="Additional worker metadata")

    @field_validator("last_heartbeat")
    @classmethod
    def validate_timestamp(cls, v: str | None) -> str | None:
        """Validate ISO timestamp format."""
        if v is None:
            return v
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid ISO timestamp: {v}") from e
        return v

    def get_available_gpus(self) -> list[GPUInfo]:
        """Get list of GPUs with capacity for more jobs."""
        max_per_gpu = self.max_concurrent_jobs
        return [gpu for gpu in self.gpus if self.current_jobs < len(self.gpus) * max_per_gpu]

    def is_available(self) -> bool:
        """Check if worker can accept new jobs."""
        if not self.enabled:
            return False
        if self.status != "online":
            return False
        max_per_gpu = self.max_concurrent_jobs
        return self.current_jobs < len(self.gpus) * max_per_gpu


class WorkerJobAssignment(BaseModel):
    """Assignment of an experiment to a specific GPU."""

    experiment_id: str
    worker_name: str
    gpu_id: str
    pid: int | None = None
    assigned_at: str
    status: Literal["assigned", "running", "completed", "failed"] = "assigned"

    @field_validator("assigned_at")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate ISO timestamp format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid ISO timestamp: {v}") from e
        return v
