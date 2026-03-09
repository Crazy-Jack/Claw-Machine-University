"""Pydantic schema for research hypotheses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Hypothesis(BaseModel):
    """Represents a research hypothesis to be tested."""

    id: str = Field(..., description="Unique hypothesis identifier")
    title: str = Field(..., description="Concise hypothesis title")
    rationale: str = Field(..., description="Scientific rationale for the hypothesis")
    expected_effect: str = Field(..., description="Expected effect if hypothesis is correct")
    priority: float = Field(1.0, ge=0.0, description="Priority for testing this hypothesis")
    related_experiments: list[str] = Field(
        default_factory=list, description="Experiment IDs testing this hypothesis"
    )
    status: Literal["active", "validated", "rejected", "stale"] = Field(
        "active", description="Current status of the hypothesis"
    )
    created_by: Literal["human", "openclaw", "system"] = Field(
        ..., description="Who created this hypothesis"
    )
    created_at: str = Field(..., description="ISO timestamp of creation")
    updated_at: str | None = Field(None, description="ISO timestamp of last update")
    validated_by_experiment: str | None = Field(None, description="Experiment ID that validated this")
    family: str | None = Field(None, description="Research family/group")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Ensure hypothesis ID starts with 'hyp_'."""
        if not v.startswith("hyp_"):
            raise ValueError("Hypothesis ID must start with 'hyp_'")
        return v
