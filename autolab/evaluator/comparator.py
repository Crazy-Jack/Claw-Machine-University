"""Comparator for comparing experiment results."""

import math
from typing import Any

from autolab.schemas.experiment import Experiment
from autolab.schemas.result import Result


class ComparisonResult(BaseModel):
    """Result of comparing two experiments."""

    experiment_id: str = Field(..., description="Current experiment ID")
    baseline_id: str = Field(..., description="Baseline experiment ID")
    primary_metric_delta: float = Field(..., description="Delta in primary metric")
    primary_metric_delta_percent: float = Field(..., description="Delta as percentage")
    is_better: bool = Field(..., description="Whether current is better than baseline")
    comparison_summary: str = Field(..., description="Human-readable summary")
    metric_comparisons: dict[str, dict] = Field(..., description="Per-metric comparisons")
    runtime_delta_seconds: float | None = Field(None, description="Runtime delta")
    resource_delta: dict[str, Any] = Field(..., description="Resource usage deltas")


class Comparator:
    """Comparator for comparing experiment results."""

    def __init__(
        self,
        primary_metric: str = "val_acc",
        higher_is_better: bool = True,
    ) -> None:
        """Initialize comparator.

        Args:
            primary_metric: Name of primary metric for ranking.
            higher_is_better: Whether higher values are better for primary metric.
        """
        self.primary_metric = primary_metric
        self.higher_is_better = higher_is_better

    def compare(
        self,
        current: Result,
        baseline: Result,
        current_experiment: Experiment,
        baseline_experiment: Experiment,
    ) -> ComparisonResult:
        """Compare a result against a baseline.

        Args:
            current: Current result.
            baseline: Baseline result.
            current_experiment: Current experiment metadata.
            baseline_experiment: Baseline experiment metadata.

        Returns:
            ComparisonResult object.
        """
        # Primary metric comparison
        primary_delta = self._compare_metric(current, baseline, self.primary_metric)

        # Per-metric comparisons
        metric_comparisons = {}
        for metric in set(list(current.metrics.keys()) + list(baseline.metrics.keys())):
            delta = self._compare_metric(current, baseline, metric)
            metric_comparisons[metric] = delta

        # Runtime comparison
        runtime_delta = None
        if current.runtime_seconds and baseline.runtime_seconds:
            runtime_delta = current.runtime_seconds - baseline.runtime_seconds

        # Resource comparison
        resource_delta = self._compare_resources(
            current_experiment,
            baseline_experiment,
        )

        # Determine if better
        is_better = self._determine_if_better(primary_delta)

        # Generate summary
        summary = self._generate_summary(
            primary_delta,
            is_better,
            runtime_delta,
        )

        return ComparisonResult(
            experiment_id=current.experiment_id,
            baseline_id=baseline.experiment_id,
            primary_metric_delta=primary_delta.get("delta", 0.0),
            primary_metric_delta_percent=primary_delta.get("delta_percent", 0.0),
            is_better=is_better,
            comparison_summary=summary,
            metric_comparisons=metric_comparisons,
            runtime_delta_seconds=runtime_delta,
            resource_delta=resource_delta,
        )

    def compare_to_best_in_family(
        self,
        current: Result,
        all_results: dict[str, Result],
        family: str,
        primary_metric: str | None = None,
    ) -> ComparisonResult | None:
        """Compare current to best result in family.

        Args:
            current: Current result.
            all_results: All results.
            family: Family name.
            primary_metric: Override primary metric.

        Returns:
            ComparisonResult or None if no family results.
        """
        metric = primary_metric or self.primary_metric

        # Find best in family
        best_result = None
        best_id = None
        best_value = None

        for result_id, result in all_results.items():
            if result_id == current.experiment_id:
                continue

            if not result.success:
                continue

            if metric not in result.metrics:
                continue

            value = float(result.metrics[metric])
            if best_value is None:
                best_value = value
                best_result = result
                best_id = result_id
                continue

            if self.higher_is_better:
                if value > best_value:
                    best_value = value
                    best_result = result
                    best_id = result_id
            else:
                if value < best_value:
                    best_value = value
                    best_result = result
                    best_id = result_id

        if best_result is None:
            return None

        # Create dummy experiments for comparison
        current_exp = Experiment(
            id=current.experiment_id,
            title="Current",
            description="",
            objective="",
            status="completed",
            config_path="",
            config_snapshot={},
            code_snapshot={},
            resource_request={},
            launch_command=[],
            working_dir="",
            planner_rationale="",
            created_by="system",
            created_at="",
        )

        baseline_exp = Experiment(
            id=best_id,
            title="Best in family",
            description="",
            objective="",
            status="completed",
            config_path="",
            config_snapshot={},
            code_snapshot={},
            resource_request={},
            launch_command=[],
            working_dir="",
            planner_rationale="",
            created_by="system",
            created_at="",
        )

        return self.compare(current, best_result, current_exp, baseline_exp)

    def rank_results(
        self,
        results: dict[str, Result],
        primary_metric: str | None = None,
    ) -> list[tuple[str, float]]:
        """Rank results by primary metric.

        Args:
            results: Dictionary of results.
            primary_metric: Override primary metric.

        Returns:
            List of (experiment_id, score) tuples sorted by score.
        """
        metric = primary_metric or self.primary_metric

        ranked = []
        for exp_id, result in results.items():
            if not result.success:
                continue

            if metric not in result.metrics:
                continue

            score = float(result.metrics[metric])
            ranked.append((exp_id, score))

        # Sort
        ranked.sort(key=lambda x: x[1], reverse=self.higher_is_better)

        return ranked

    def get_improvement_stats(
        self,
        results: list[Result],
        metric: str | None = None,
    ) -> dict[str, Any]:
        """Get improvement statistics across results.

        Args:
            results: List of results in chronological order.
            metric: Metric to analyze.

        Returns:
            Dictionary with improvement stats.
        """
        metric = metric or self.primary_metric

        values = []
        for result in results:
            if not result.success:
                continue
            if metric in result.metrics:
                values.append(float(result.metrics[metric]))

        if len(values) < 2:
            return {
                "metric": metric,
                "count": len(values),
                "improvements": [],
            }

        improvements = []
        for i in range(1, len(values)):
            prev_val = values[i - 1]
            curr_val = values[i]
            delta = curr_val - prev_val
            delta_percent = (delta / prev_val * 100) if prev_val != 0 else 0

            improvements.append({
                "step": i,
                "previous": prev_val,
                "current": curr_val,
                "delta": delta,
                "delta_percent": delta_percent,
                "is_improvement": (delta > 0) if self.higher_is_better else (delta < 0),
            })

        total_improvement = values[-1] - values[0]
        total_improvement_percent = (total_improvement / values[0] * 100) if values[0] != 0 else 0

        return {
            "metric": metric,
            "count": len(values),
            "first_value": values[0],
            "last_value": values[-1],
            "total_improvement": total_improvement,
            "total_improvement_percent": total_improvement_percent,
            "improvements": improvements,
            "num_improvements": sum(1 for imp in improvements if imp["is_improvement"]),
        }

    def _compare_metric(
        self,
        current: Result,
        baseline: Result,
        metric_name: str,
    ) -> dict[str, Any]:
        """Compare a single metric.

        Args:
            current: Current result.
            baseline: Baseline result.
            metric_name: Name of metric.

        Returns:
            Dictionary with comparison data.
        """
        current_value = current.metrics.get(metric_name)
        baseline_value = baseline.metrics.get(metric_name)

        if current_value is None or baseline_value is None:
            return {
                "metric": metric_name,
                "current": current_value,
                "baseline": baseline_value,
                "delta": None,
                "delta_percent": None,
                "available": False,
            }

        try:
            current_val = float(current_value)
            baseline_val = float(baseline_value)

            delta = current_val - baseline_val
            delta_percent = (delta / baseline_val * 100) if baseline_val != 0 else 0

            is_better = (delta > 0) if self.higher_is_better else (delta < 0)

            return {
                "metric": metric_name,
                "current": current_val,
                "baseline": baseline_val,
                "delta": delta,
                "delta_percent": delta_percent,
                "available": True,
                "is_better": is_better,
            }
        except (ValueError, TypeError):
            return {
                "metric": metric_name,
                "current": current_value,
                "baseline": baseline_value,
                "delta": None,
                "delta_percent": None,
                "available": False,
            }

    def _compare_resources(
        self,
        current_exp: Experiment,
        baseline_exp: Experiment,
    ) -> dict[str, Any]:
        """Compare resource requirements.

        Args:
            current_exp: Current experiment.
            baseline_exp: Baseline experiment.

        Returns:
            Dictionary with resource deltas.
        """
        current_res = current_exp.resource_request
        baseline_res = baseline_exp.resource_request

        return {
            "gpu_memory_gb_delta": current_res.get("gpu_memory_gb", 0) - baseline_res.get("gpu_memory_gb", 0),
            "batch_size_delta": current_res.get("batch_size", 0) - baseline_res.get("batch_size", 0),
            "max_runtime_delta": (current_exp.max_runtime_minutes or 0) - (baseline_exp.max_runtime_minutes or 0),
        }

    def _determine_if_better(self, primary_delta: dict) -> bool:
        """Determine if current result is better.

        Args:
            primary_delta: Primary metric comparison.

        Returns:
            True if better.
        """
        if not primary_delta.get("available", False):
            return False

        delta = primary_delta.get("delta", 0)
        if self.higher_is_better:
            return delta > 0
        else:
            return delta < 0

    def _generate_summary(
        self,
        primary_delta: dict,
        is_better: bool,
        runtime_delta: float | None,
    ) -> str:
        """Generate comparison summary.

        Args:
            primary_delta: Primary metric comparison.
            is_better: Whether better.
            runtime_delta: Runtime delta.

        Returns:
            Summary string.
        """
        if not primary_delta.get("available", False):
            return "Primary metric not available for comparison"

        direction = "↑" if is_better else "↓"
        delta = primary_delta.get("delta", 0)
        delta_percent = primary_delta.get("delta_percent", 0)

        parts = [f"{direction} {abs(delta_percent):.2f}% on primary metric"]

        if runtime_delta is not None:
            runtime_delta_min = runtime_delta / 60
            if runtime_delta > 60:
                parts.append(f"runtime +{runtime_delta_min:.1f}m")
            elif runtime_delta < -60:
                parts.append(f"runtime {runtime_delta_min:.1f}m (faster)")

        status = "better" if is_better else "worse"
        return f"{status} ({', '.join(parts)})"


from pydantic import BaseModel, Field
