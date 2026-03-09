"""Result summarizer for generating experiment result summaries."""

import os
from datetime import datetime, timedelta
from typing import Any

from autolab.schemas.experiment import Experiment
from autolab.schemas.result import Result


class ResultSummarizer:
    """Summarizer for experiment results."""

    def __init__(self) -> None:
        """Initialize result summarizer."""
        pass

    def summarize_result(
        self,
        experiment: Experiment,
        result: Result,
    ) -> str:
        """Generate a summary of an experiment result.

        Args:
            experiment: Experiment object.
            result: Result object.

        Returns:
            Summary string.
        """
        lines = []

        # Title
        lines.append(f"# Experiment {experiment.id}: {experiment.title}")
        lines.append("")

        # Status
        status_str = "✅ Success" if result.success else "❌ Failed"
        lines.append(f"**Status:** {status_str}")
        lines.append("")

        # Objective
        lines.append(f"**Objective:** {experiment.objective}")
        lines.append("")

        # Metrics
        if result.metrics:
            lines.append("**Metrics:**")
            for key, value in sorted(result.metrics.items()):
                lines.append(f"  - {key}: {value}")
            lines.append("")

        # Runtime info
        if result.runtime_seconds:
            runtime_min = result.runtime_seconds / 60
            lines.append(f"**Runtime:** {runtime_min:.1f} minutes")
        if result.gpu_id:
            lines.append(f"**GPU:** {result.gpu_id}")
        if result.host:
            lines.append(f"**Host:** {result.host}")
        lines.append("")

        # Failure info
        if not result.success:
            if result.failure_type:
                lines.append(f"**Failure Type:** {result.failure_type}")
            if result.failure_reason:
                lines.append(f"**Failure Reason:** {result.failure_reason}")
            if result.exit_code is not None:
                lines.append(f"**Exit Code:** {result.exit_code}")
            lines.append("")

        # Comparison
        if result.comparison:
            lines.append("**Comparison:**")
            for key, value in result.comparison.items():
                lines.append(f"  - {key}: {value}")
            lines.append("")

        # Artifacts
        if result.artifact_paths:
            lines.append("**Artifacts:**")
            for path in result.artifact_paths:
                lines.append(f"  - {path}")
            lines.append("")

        # Log paths
        lines.append("**Logs:**")
        lines.append(f"  - stdout: {result.log_path}")
        if result.stderr_path:
            lines.append(f"  - stderr: {result.stderr_path}")
        lines.append("")

        # Rationale
        if experiment.planner_rationale:
            lines.append("**Planner Rationale:**")
            lines.append(experiment.planner_rationale)
            lines.append("")

        return "\n".join(lines)

    def get_short_summary(self, result: Result) -> str:
        """Get a short one-line summary.

        Args:
            result: Result object.

        Returns:
            Short summary string.
        """
        if result.success:
            metric_str = ""
            if result.metrics:
                metrics = ", ".join(f"{k}={v}" for k, v in list(result.metrics.items())[:3])
                metric_str = f" ({metrics})"
            return f"✅ Success{metric_str}"
        else:
            failure = result.failure_type or "failed"
            return f"❌ {failure}"

    def get_result_score(self, result: Result, primary_metric: str | None = None) -> float:
        """Calculate a score for a result.

        Args:
            result: Result object.
            primary_metric: Primary metric to use for scoring.

        Returns:
            Score (higher is better).
        """
        if not result.success:
            return -1.0

        if not result.metrics:
            return 0.0

        # Use primary metric if specified
        if primary_metric and primary_metric in result.metrics:
            value = float(result.metrics[primary_metric])
            return value

        # Otherwise, use first metric
        first_metric = next(iter(result.metrics.values()))
        return float(first_metric)

    def get_comparison_string(
        self,
        baseline_value: float,
        current_value: float,
        metric_name: str,
        higher_is_better: bool = True,
    ) -> str:
        """Get a comparison string between two values.

        Args:
            baseline_value: Baseline metric value.
            current_value: Current metric value.
            metric_name: Name of metric.
            higher_is_better: Whether higher is better.

        Returns:
            Comparison string.
        """
        delta = current_value - baseline_value
        delta_percent = (delta / baseline_value * 100) if baseline_value != 0 else 0

        if higher_is_better:
            if delta > 0:
                direction = "↑"
                status = "better"
            elif delta < 0:
                direction = "↓"
                status = "worse"
            else:
                direction = "→"
                status = "same"
        else:
            # Lower is better (e.g., loss)
            if delta < 0:
                direction = "↓"
                status = "better"
            elif delta > 0:
                direction = "↑"
                status = "worse"
            else:
                direction = "→"
                status = "same"

        return f"{metric_name}: {direction} {abs(delta_percent):.2f}% ({current_value:.4f} vs {baseline_value:.4f}, {status})"

    def get_runtime_stats(self, result: Result) -> dict[str, Any]:
        """Get runtime statistics.

        Args:
            result: Result object.

        Returns:
            Dictionary with runtime stats.
        """
        stats = {
            "runtime_seconds": result.runtime_seconds,
            "runtime_minutes": result.runtime_seconds / 60 if result.runtime_seconds else None,
            "runtime_hours": result.runtime_seconds / 3600 if result.runtime_seconds else None,
        }

        if result.runtime_seconds:
            stats["human_readable"] = self._format_duration(result.runtime_seconds)

        return stats

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format.

        Args:
            seconds: Duration in seconds.

        Returns:
            Human-readable string.
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            minutes = (seconds % 3600) / 60
            return f"{hours:.1f}h {minutes:.0f}m"

    def extract_key_insights(
        self,
        result: Result,
        experiment: Experiment,
    ) -> list[str]:
        """Extract key insights from a result.

        Args:
            result: Result object.
            experiment: Experiment object.

        Returns:
            List of insight strings.
        """
        insights = []

        if result.success:
            # Success insights
            if result.metrics:
                top_metrics = sorted(
                    result.metrics.items(),
                    key=lambda x: float(x[1]) if isinstance(x[1], (int, float)) else 0,
                    reverse=True,
                )[:3]
                for metric, value in top_metrics:
                    insights.append(f"Achieved {metric}: {value}")

            # Runtime insight
            if result.runtime_seconds:
                runtime_min = result.runtime_seconds / 60
                if runtime_min < 60:
                    insights.append(f"Fast training: {runtime_min:.1f} minutes")
                elif runtime_min > 360:
                    insights.append(f"Long training: {runtime_min / 60:.1f} hours")
        else:
            # Failure insights
            if result.failure_type:
                insights.append(f"Failed with {result.failure_type}")

            if result.failure_reason:
                insights.append(f"Reason: {result.failure_reason[:100]}")

        return insights
