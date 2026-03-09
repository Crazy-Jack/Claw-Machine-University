"""Pydantic schema for experiment results."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Result(BaseModel):
    """Represents the result of a completed or failed experiment."""

    experiment_id: str = Field(..., description="Associated experiment ID")
    success: bool = Field(..., description="Whether the experiment completed successfully")
    metrics: dict[str, float | int | str] = Field(
        default_factory=dict, description="Extracted metrics from the run"
    )
    summary: str = Field(..., description="Human-readable summary of the result")
    comparison: dict[str, Any] = Field(
        default_factory=dict,
        description="Comparison against baseline/parent/family best",
    )
    log_path: str = Field(..., description="Path to stdout log file")
    stderr_path: str | None = Field(None, description="Path to stderr log file")
    artifact_paths: list[str] = Field(
        default_factory=list, description="Paths to generated artifacts"
    )
    runtime_seconds: float | None = Field(None, ge=0, description="Runtime in seconds")
    gpu_id: str | None = Field(None, description="GPU ID used")
    host: str | None = Field(None, description="Worker hostname")
    exit_code: int | None = Field(None, description="Process exit code")
    failure_type: str | None = Field(
        None,
        description="Type of failure if failed (oom, timeout, syntax_error, etc.)",
    )
    failure_reason: str | None = Field(None, description="Detailed failure reason")
    parsed_at: str = Field(..., description="ISO timestamp when result was parsed")
    gpu_utilization: float | None = Field(None, ge=0, le=100, description="Average GPU utilization %")
    peak_memory_gb: float | None = Field(None, ge=0, description="Peak GPU memory usage in GB")

    @field_validator("parsed_at")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate ISO timestamp format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid ISO timestamp: {v}") from e
        return v

    @field_validator("exit_code")
    @classmethod
    def validate_exit_code(cls, v: int | None) -> int | None:
        """Exit code should be non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("Exit code must be non-negative")
        return v


class ComparisonMetrics(BaseModel):
    """Metrics comparing an experiment against a baseline."""

    baseline_experiment_id: str = Field(..., description="Baseline experiment ID")
    primary_metric_delta: float = Field(..., description="Delta in primary metric vs baseline")
    runtime_delta_seconds: float | None = Field(None, description="Delta in runtime vs baseline")
    is_better: bool = Field(..., description="Whether this result is better than baseline")
    notes: str = Field(..., description="Additional comparison notes")
