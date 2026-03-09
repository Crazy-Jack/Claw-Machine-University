"""Pydantic schema for experiments."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Experiment(BaseModel):
    """Represents an ML experiment in the queue or running/completed."""

    id: str = Field(..., description="Unique experiment identifier")
    hypothesis_id: str | None = Field(None, description="Associated hypothesis ID if any")
    title: str = Field(..., description="Human-readable experiment title")
    description: str = Field(..., description="Detailed experiment description")
    objective: str = Field(..., description="Research objective this experiment addresses")
    family: str | None = Field(None, description="Experiment family/group for comparison")
    parent_experiment_id: str | None = Field(None, description="Parent experiment if branching")
    baseline_experiment_id: str | None = Field(None, description="Baseline experiment for comparison")
    status: Literal[
        "pending",
        "ready",
        "running",
        "completed",
        "failed",
        "blocked",
        "canceled",
    ] = Field(..., description="Current experiment status")
    priority: float = Field(1.0, ge=0.0, description="Experiment priority for scheduling")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    dependencies: list[str] = Field(default_factory=list, description="Experiment IDs that must complete first")
    config_path: str = Field(..., description="Path to experiment configuration file")
    config_snapshot: dict = Field(..., description="Snapshot of configuration at creation")
    code_snapshot: dict = Field(..., description="Git snapshot of code at creation")
    resource_request: dict = Field(..., description="Requested resources (GPU, memory, etc.)")
    launch_command: list[str] = Field(..., description="Command to launch the experiment")
    working_dir: str = Field(..., description="Working directory for the experiment")
    dataset_info: dict = Field(default_factory=dict, description="Dataset information")
    planner_rationale: str = Field(..., description="Rationale from planner for this experiment")
    created_by: Literal["human", "openclaw", "system"] = Field(
        ..., description="Who created this experiment"
    )
    max_runtime_minutes: int | None = Field(None, ge=0, description="Maximum allowed runtime")
    retry_count: int = Field(0, ge=0, description="Number of times this experiment has been retried")
    max_retries: int = Field(1, ge=0, description="Maximum number of retries allowed")
    created_at: str = Field(..., description="ISO timestamp of creation")
    started_at: str | None = Field(None, description="ISO timestamp when started")
    finished_at: str | None = Field(None, description="ISO timestamp when finished")
    worker_name: str | None = Field(None, description="Worker name where running/ran")
    gpu_id: str | None = Field(None, description="GPU ID where running/ran")
    pid: int | None = Field(None, description="Process ID on worker")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Ensure experiment ID starts with 'exp_'."""
        if not v.startswith("exp_"):
            raise ValueError("Experiment ID must start with 'exp_'")
        return v

    @field_validator("created_at", "started_at", "finished_at")
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
