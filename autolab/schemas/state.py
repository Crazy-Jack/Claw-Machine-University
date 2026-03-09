"""Pydantic schema for global state."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ResearchGoal(BaseModel):
    """Represents the current research goal."""

    title: str = Field(..., description="Goal title")
    description: str = Field(..., description="Detailed goal description")
    objectives: list[str] = Field(..., description="List of specific objectives")
    constraints: list[str] = Field(default_factory=list, description="Constraints and limitations")
    baseline_experiment_id: str | None = Field(None, description="Primary baseline experiment")
    target_metrics: dict[str, float] = Field(
        default_factory=dict, description="Target metric values to achieve"
    )
    created_at: str = Field(..., description="ISO timestamp of goal creation")


class GlobalState(BaseModel):
    """Global state of the autonomous lab."""

    goal: ResearchGoal = Field(..., description="Current research goal")
    lab_status: "LabStatus" = Field(..., description="Lab status information")
    recent_history: list[str] = Field(
        default_factory=list, description="Recent experiment IDs in order"
    )
    best_results: dict[str, str] = Field(
        default_factory=dict, description="Best experiment per family/metric"
    )
    baselines: dict[str, str] = Field(
        default_factory=dict, description="Baseline experiment IDs per family"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    updated_at: str = Field(..., description="ISO timestamp of last update")

    @field_validator("updated_at")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate ISO timestamp format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid ISO timestamp: {v}") from e
        return v


class LabStatus(BaseModel):
    """Status of the lab operations."""

    controller_pid: int | None = Field(None, description="Controller process ID")
    cycle_count: int = Field(0, ge=0, description="Number of completed cycles")
    total_experiments: int = Field(0, ge=0, description="Total experiments created")
    completed_experiments: int = Field(0, ge=0, description="Successfully completed experiments")
    failed_experiments: int = Field(0, ge=0, description="Failed experiments")
    running_experiments: int = Field(0, ge=0, description="Currently running experiments")
    last_cycle_time: str | None = Field(None, description="ISO timestamp of last cycle")
    uptime_seconds: float = Field(0.0, ge=0, description="Controller uptime in seconds")


class QueueSummary(BaseModel):
    """Summary of the experiment queue."""

    pending: int = Field(0, ge=0, description="Pending experiments")
    ready: int = Field(0, ge=0, description="Ready to run experiments")
    running: int = Field(0, ge=0, description="Currently running experiments")
    blocked: int = Field(0, ge=0, description="Blocked by dependencies")
    total: int = Field(0, ge=0, description="Total experiments in queue")


class FailureSummary(BaseModel):
    """Summary of recent failures."""

    total_failures: int = Field(0, ge=0)
    recurring_failures: list[dict] = Field(default_factory=list, description="Recurring failure patterns")
    recent_failure_types: list[str] = Field(default_factory=list)
