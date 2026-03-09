"""Pydantic schema for planner actions."""

from typing import Literal

from pydantic import BaseModel, Field


class PlannerAction(BaseModel):
    """Represents an action proposed by the planner."""

    action_type: Literal[
        "create_experiment",
        "create_hypothesis",
        "patch_config",
        "patch_code",
        "rerank_queue",
        "archive_branch",
        "stop_branch",
        "request_report",
        "retry_experiment",
    ] = Field(..., description="Type of action to perform")
    payload: dict = Field(..., description="Action-specific payload")
    rationale: str = Field(..., description="Reasoning behind this action")


class CreateExperimentPayload(BaseModel):
    """Payload for creating a new experiment."""

    title: str
    description: str
    objective: str
    family: str | None = None
    parent_experiment_id: str | None = None
    baseline_experiment_id: str | None = None
    priority: float = 1.0
    tags: list[str] = []
    dependencies: list[str] = []
    config_patch: dict | None = None
    config_path: str | None = None
    resource_request: dict = {}
    launch_command: list[str] = []
    working_dir: str = "."
    dataset_info: dict = {}
    max_runtime_minutes: int | None = None


class CreateHypothesisPayload(BaseModel):
    """Payload for creating a new hypothesis."""

    title: str
    rationale: str
    expected_effect: str
    priority: float = 1.0
    family: str | None = None
    tags: list[str] = []


class PatchConfigPayload(BaseModel):
    """Payload for patching an experiment configuration."""

    experiment_id: str
    config_patch: dict


class PatchCodePayload(BaseModel):
    """Payload for patching code."""

    target_file: str
    patch_content: str
    experiment_id: str | None = None
    validation_required: bool = True


class RerankQueuePayload(BaseModel):
    """Payload for reranking the experiment queue."""

    experiment_priorities: dict[str, float]
    rationale: str


class StopBranchPayload(BaseModel):
    """Payload for stopping a branch of experiments."""

    experiment_id: str  # Root of the branch
    reason: str
    cancel_running: bool = False


class RequestReportPayload(BaseModel):
    """Payload for generating a report."""

    report_type: Literal["cycle", "experiment", "family", "summary"]
    scope: str | None = None  # experiment_id or family name
    include_plots: bool = False
