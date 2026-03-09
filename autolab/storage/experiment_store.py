"""Experiment store for persistent storage of experiments."""

import json
from pathlib import Path
from typing import Any

from autolab.schemas.experiment import Experiment


class ExperimentStore:
    """Persistent storage for experiments."""

    def __init__(self, workspace_path: str = "./autolab_workspace") -> None:
        """Initialize the experiment store.

        Args:
            workspace_path: Path to the workspace directory.
        """
        self.workspace_path = Path(workspace_path).expanduser().resolve()
        self.state_dir = self.workspace_path / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.experiments_file = self.state_dir / "experiments.json"

    def load_all(self) -> dict[str, Experiment]:
        """Load all experiments from disk.

        Returns:
            Dictionary mapping experiment IDs to Experiment objects.
        """
        if not self.experiments_file.exists():
            return {}

        with open(self.experiments_file) as f:
            data = json.load(f)

        return {exp["id"]: Experiment(**exp) for exp in data}

    def save_all(self, experiments: dict[str, Experiment]) -> None:
        """Save all experiments to disk.

        Args:
            experiments: Dictionary mapping experiment IDs to Experiment objects.
        """
        data = [exp.model_dump() for exp in experiments.values()]
        with open(self.experiments_file, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, experiment_id: str) -> Experiment | None:
        """Load a single experiment.

        Args:
            experiment_id: ID of experiment to load.

        Returns:
            Experiment object or None if not found.
        """
        experiments = self.load_all()
        return experiments.get(experiment_id)

    def save(self, experiment: Experiment) -> None:
        """Save an experiment to disk.

        Args:
            experiment: Experiment object to save.
        """
        experiments = self.load_all()
        experiments[experiment.id] = experiment
        self.save_all(experiments)

    def add(self, experiment: Experiment) -> None:
        """Add a new experiment.

        Args:
            experiment: Experiment to add.

        Raises:
            ValueError: If experiment ID already exists.
        """
        experiments = self.load_all()
        if experiment.id in experiments:
            raise ValueError(f"Experiment {experiment.id} already exists")
        self.save(experiment)

    def update(
        self,
        experiment_id: str,
        **updates: Any,
    ) -> None:
        """Update an experiment.

        Args:
            experiment_id: ID of experiment to update.
            **updates: Fields to update.

        Raises:
            ValueError: If experiment not found.
        """
        experiments = self.load_all()
        if experiment_id not in experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        exp_data = experiments[experiment_id].model_dump()
        exp_data.update(updates)
        experiments[experiment_id] = Experiment(**exp_data)
        self.save_all(experiments)

    def delete(self, experiment_id: str) -> None:
        """Delete an experiment.

        Args:
            experiment_id: ID of experiment to delete.

        Raises:
            ValueError: If experiment not found.
        """
        experiments = self.load_all()
        if experiment_id not in experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        del experiments[experiment_id]
        self.save_all(experiments)

    def get_by_status(
        self,
        status: str,
    ) -> dict[str, Experiment]:
        """Get experiments by status.

        Args:
            status: Status to filter by.

        Returns:
            Dictionary of experiments with matching status.
        """
        experiments = self.load_all()
        return {eid: exp for eid, exp in experiments.items() if exp.status == status}

    def get_by_family(self, family: str) -> dict[str, Experiment]:
        """Get experiments by family.

        Args:
            family: Family name.

        Returns:
            Dictionary of experiments in the family.
        """
        experiments = self.load_all()
        return {eid: exp for eid, exp in experiments.items() if exp.family == family}

    def get_by_hypothesis(
        self,
        hypothesis_id: str,
    ) -> dict[str, Experiment]:
        """Get experiments by hypothesis.

        Args:
            hypothesis_id: Hypothesis ID.

        Returns:
            Dictionary of experiments testing the hypothesis.
        """
        experiments = self.load_all()
        return {eid: exp for eid, exp in experiments.items() if exp.hypothesis_id == hypothesis_id}

    def get_ready_experiments(
        self,
    ) -> dict[str, Experiment]:
        """Get experiments that are ready to run.

        Returns:
            Dictionary of experiments with status 'ready'.
        """
        return self.get_by_status("ready")

    def get_running_experiments(
        self,
    ) -> dict[str, Experiment]:
        """Get currently running experiments.

        Returns:
            Dictionary of experiments with status 'running'.
        """
        return self.get_by_status("running")

    def get_pending_experiments(
        self,
    ) -> dict[str, Experiment]:
        """Get pending experiments.

        Returns:
            Dictionary of experiments with status 'pending'.
        """
        return self.get_by_status("pending")

    def check_dependencies(
        self,
        experiment_id: str,
        completed_experiments: set[str],
    ) -> bool:
        """Check if an experiment's dependencies are satisfied.

        Args:
            experiment_id: ID of experiment to check.
            completed_experiments: Set of completed experiment IDs.

        Returns:
            True if all dependencies are satisfied.
        """
        experiment = self.load(experiment_id)
        if experiment is None:
            return False

        if not experiment.dependencies:
            return True

        return all(dep in completed_experiments for dep in experiment.dependencies)

    def update_dependencies_satisfied(self) -> dict[str, Experiment]:
        """Update experiments whose dependencies are now satisfied.

        Returns:
            Dictionary of experiments whose status was updated from pending to ready.
        """
        experiments = self.load_all()
        completed = {eid for eid, exp in experiments.items() if exp.status == "completed"}

        updated = {}
        for eid, exp in experiments.items():
            if exp.status == "pending":
                if all(dep in completed for dep in exp.dependencies):
                    exp.status = "ready"
                    updated[eid] = exp

        if updated:
            experiments.update(updated)
            self.save_all(experiments)

        return updated
