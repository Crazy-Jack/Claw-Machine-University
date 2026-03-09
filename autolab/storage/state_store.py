"""State store for persistent storage of lab state."""

import json
import os
from pathlib import Path
from typing import Any

from autolab.schemas.config import SystemConfig
from autolab.schemas.experiment import Experiment
from autolab.schemas.hypothesis import Hypothesis
from autolab.schemas.result import Result
from autolab.schemas.state import (
    FailureSummary,
    GlobalState,
    LabStatus,
    QueueSummary,
    ResearchGoal,
)


class StateStore:
    """Persistent storage for lab state."""

    def __init__(self, workspace_path: str = "./autolab_workspace") -> None:
        """Initialize the state store.

        Args:
            workspace_path: Path to the workspace directory.
        """
        self.workspace_path = Path(workspace_path).expanduser().resolve()
        self.state_dir = self.workspace_path / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # State files
        self.global_state_file = self.state_dir / "global_state.json"
        self.hypotheses_file = self.state_dir / "hypotheses.json"
        self.baselines_file = self.state_dir / "baselines.json"

    def load_global_state(self) -> GlobalState:
        """Load global state from disk.

        Returns:
            GlobalState object with current lab state.
        """
        if not self.global_state_file.exists():
            # Create default state
            return self._create_default_state()

        with open(self.global_state_file) as f:
            data = json.load(f)

        return GlobalState(**data)

    def save_global_state(self, state: GlobalState) -> None:
        """Save global state to disk.

        Args:
            state: GlobalState object to save.
        """
        with open(self.global_state_file, "w") as f:
            json.dump(state.model_dump(), f, indent=2)

    def load_hypotheses(self) -> dict[str, Hypothesis]:
        """Load all hypotheses from disk.

        Returns:
            Dictionary mapping hypothesis IDs to Hypothesis objects.
        """
        if not self.hypotheses_file.exists():
            return {}

        with open(self.hypotheses_file) as f:
            data = json.load(f)

        return {h["id"]: Hypothesis(**h) for h in data}

    def save_hypotheses(self, hypotheses: dict[str, Hypothesis]) -> None:
        """Save hypotheses to disk.

        Args:
            hypotheses: Dictionary mapping hypothesis IDs to Hypothesis objects.
        """
        data = [h.model_dump() for h in hypotheses.values()]
        with open(self.hypotheses_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        """Add a hypothesis to the store.

        Args:
            hypothesis: Hypothesis to add.
        """
        hypotheses = self.load_hypotheses()
        hypotheses[hypothesis.id] = hypothesis
        self.save_hypotheses(hypotheses)

    def update_hypothesis(self, hypothesis_id: str, **updates: Any) -> None:
        """Update a hypothesis.

        Args:
            hypothesis_id: ID of hypothesis to update.
            **updates: Fields to update.
        """
        hypotheses = self.load_hypotheses()
        if hypothesis_id not in hypotheses:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")

        hyp_data = hypotheses[hypothesis_id].model_dump()
        hyp_data.update(updates)
        hypotheses[hypothesis_id] = Hypothesis(**hyp_data)
        self.save_hypotheses(hypotheses)

    def load_baselines(self) -> dict[str, str]:
        """Load baseline experiment IDs per family.

        Returns:
            Dictionary mapping family names to baseline experiment IDs.
        """
        if not self.baselines_file.exists():
            return {}

        with open(self.baselines_file) as f:
            return json.load(f)

    def save_baselines(self, baselines: dict[str, str]) -> None:
        """Save baseline experiment IDs per family.

        Args:
            baselines: Dictionary mapping family names to baseline experiment IDs.
        """
        with open(self.baselines_file, "w") as f:
            json.dump(baselines, f, indent=2)

    def set_baseline(self, family: str, experiment_id: str) -> None:
        """Set a baseline experiment for a family.

        Args:
            family: Family name.
            experiment_id: Experiment ID to use as baseline.
        """
        baselines = self.load_baselines()
        baselines[family] = experiment_id
        self.save_baselines(baselines)

    def _create_default_state(self) -> GlobalState:
        """Create default global state.

        Returns:
            Default GlobalState object.
        """
        goal = ResearchGoal(
            title="Default Research Goal",
            description="Set a research goal to get started",
            objectives=["Improve model performance"],
            created_at=_get_iso_timestamp(),
        )

        status = LabStatus(
            cycle_count=0,
            total_experiments=0,
            completed_experiments=0,
            failed_experiments=0,
            running_experiments=0,
        )

        return GlobalState(
            goal=goal,
            lab_status=status,
            recent_history=[],
            best_results={},
            baselines={},
            metadata={},
            updated_at=_get_iso_timestamp(),
        )

    def get_queue_summary(self, experiments: dict[str, Experiment]) -> QueueSummary:
        """Get queue summary.

        Args:
            experiments: Dictionary of all experiments.

        Returns:
            QueueSummary object.
        """
        summary = QueueSummary()
        for exp in experiments.values():
            if exp.status == "pending":
                summary.pending += 1
            elif exp.status == "ready":
                summary.ready += 1
            elif exp.status == "running":
                summary.running += 1
            elif exp.status == "blocked":
                summary.blocked += 1
        summary.total = len(experiments)
        return summary

    def get_failure_summary(
        self,
        results: dict[str, Result],
    ) -> FailureSummary:
        """Get failure summary.

        Args:
            results: Dictionary of all results.

        Returns:
            FailureSummary object.
        """
        failed_results = [r for r in results.values() if not r.success]

        # Count by failure type
        failure_types = {}
        for r in failed_results:
            if r.failure_type:
                failure_types[r.failure_type] = failure_types.get(r.failure_type, 0) + 1

        return FailureSummary(
            total_failures=len(failed_results),
            recurring_failures=[],
            recent_failure_types=list(failure_types.keys()),
        )


def _get_iso_timestamp() -> str:
    """Get current ISO timestamp.

    Returns:
        ISO formatted timestamp string.
    """
    from datetime import datetime

    return datetime.utcnow().isoformat() + "Z"
