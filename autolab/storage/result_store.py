"""Result store for persistent storage of experiment results."""

import json
from pathlib import Path
from typing import Any

from autolab.schemas.result import Result


class ResultStore:
    """Persistent storage for experiment results."""

    def __init__(self, workspace_path: str = "./autolab_workspace") -> None:
        """Initialize the result store.

        Args:
            workspace_path: Path to the workspace directory.
        """
        self.workspace_path = Path(workspace_path).expanduser().resolve()
        self.state_dir = self.workspace_path / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.results_file = self.state_dir / "results.json"

    def load_all(self) -> dict[str, Result]:
        """Load all results from disk.

        Returns:
            Dictionary mapping experiment IDs to Result objects.
        """
        if not self.results_file.exists():
            return {}

        with open(self.results_file) as f:
            data = json.load(f)

        return {result["experiment_id"]: Result(**result) for result in data}

    def save_all(self, results: dict[str, Result]) -> None:
        """Save all results to disk.

        Args:
            results: Dictionary mapping experiment IDs to Result objects.
        """
        data = [result.model_dump() for result in results.values()]
        with open(self.results_file, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, experiment_id: str) -> Result | None:
        """Load a single result.

        Args:
            experiment_id: ID of experiment to load result for.

        Returns:
            Result object or None if not found.
        """
        results = self.load_all()
        return results.get(experiment_id)

    def save(self, result: Result) -> None:
        """Save a result to disk.

        Args:
            result: Result object to save.
        """
        results = self.load_all()
        results[result.experiment_id] = result
        self.save_all(results)

    def delete(self, experiment_id: str) -> None:
        """Delete a result.

        Args:
            experiment_id: ID of experiment to delete result for.

        Raises:
            ValueError: If result not found.
        """
        results = self.load_all()
        if experiment_id not in results:
            raise ValueError(f"Result for experiment {experiment_id} not found")

        del results[experiment_id]
        self.save_all(results)

    def get_successful(self) -> dict[str, Result]:
        """Get all successful results.

        Returns:
            Dictionary of successful results.
        """
        results = self.load_all()
        return {eid: r for eid, r in results.items() if r.success}

    def get_failed(self) -> dict[str, Result]:
        """Get all failed results.

        Returns:
            Dictionary of failed results.
        """
        results = self.load_all()
        return {eid: r for eid, r in results.items() if not r.success}

    def get_by_failure_type(self, failure_type: str) -> dict[str, Result]:
        """Get results by failure type.

        Args:
            failure_type: Type of failure to filter by.

        Returns:
            Dictionary of results with matching failure type.
        """
        results = self.load_all()
        return {
            eid: r for eid, r in results.items()
            if not r.success and r.failure_type == failure_type
        }

    def get_by_metric_range(
        self,
        metric_name: str,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> dict[str, Result]:
        """Get results filtered by metric range.

        Args:
            metric_name: Name of metric to filter on.
            min_value: Minimum metric value (inclusive).
            max_value: Maximum metric value (inclusive).

        Returns:
            Dictionary of results with metric in specified range.
        """
        results = self.get_successful()
        filtered = {}

        for eid, r in results.items():
            if metric_name not in r.metrics:
                continue

            metric_value = float(r.metrics[metric_name])

            if min_value is not None and metric_value < min_value:
                continue
            if max_value is not None and metric_value > max_value:
                continue

            filtered[eid] = r

        return filtered

    def get_best_for_metric(
        self,
        metric_name: str,
        higher_is_better: bool = True,
    ) -> Result | None:
        """Get the best result for a given metric.

        Args:
            metric_name: Name of metric to optimize.
            higher_is_better: Whether higher values are better.

        Returns:
            Best Result or None if no results found.
        """
        results = self.get_successful()
        if not results:
            return None

        best_result = None
        best_value = None

        for r in results.values():
            if metric_name not in r.metrics:
                continue

            metric_value = float(r.metrics[metric_name])

            if best_value is None:
                best_value = metric_value
                best_result = r
                continue

            if higher_is_better:
                if metric_value > best_value:
                    best_value = metric_value
                    best_result = r
            else:
                if metric_value < best_value:
                    best_value = metric_value
                    best_result = r

        return best_result
