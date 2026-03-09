"""Markdown report generator for Autolab."""

from datetime import datetime
from pathlib import Path
from typing import Any

from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.hypothesis_store import HypothesisStore
from autolab.storage.result_store import ResultStore


class MarkdownReportGenerator:
    """Generate markdown reports for Autolab."""

    def __init__(self, workspace_path: str = "./autolab_workspace") -> None:
        """Initialize report generator.

        Args:
            workspace_path: Path to workspace directory.
        """
        self.workspace_path = Path(workspace_path).expanduser().resolve()
        self.experiment_store = ExperimentStore(str(self.workspace_path))
        self.result_store = ResultStore(str(self.workspace_path))
        self.hypothesis_store = HypothesisStore(str(self.workspace_path))

    def generate_experiment_report(
        self,
        experiment_id: str,
        include_results: bool = True,
    ) -> str:
        """Generate a markdown report for a single experiment.

        Args:
            experiment_id: Experiment ID.
            include_results: Whether to include results.

        Returns:
            Markdown report string.
        """
        experiment = self.experiment_store.load(experiment_id)

        if not experiment:
            return f"# Experiment {experiment_id} Not Found\n\nExperiment does not exist."

        lines = [
            f"# Experiment Report: {experiment.title}",
            f"**ID:** `{experiment.id}`",
            f"**Status:** {experiment.status}",
            "",
            "## Overview",
            f"- **Description:** {experiment.description}",
            f"- **Objective:** {experiment.objective}",
            f"- **Family:** {experiment.family or 'N/A'}",
            f"- **Priority:** {experiment.priority}",
            f"- **Created:** {experiment.created_at}",
        ]

        if experiment.started_at:
            lines.append(f"- **Started:** {experiment.started_at}")

        if experiment.finished_at:
            lines.append(f"- **Finished:** {experiment.finished_at}")

            # Calculate duration
            try:
                started = datetime.fromisoformat(experiment.started_at.replace("Z", ""))
                finished = datetime.fromisoformat(experiment.finished_at.replace("Z", ""))
                duration = (finished - started).total_seconds() / 60
                lines.append(f"- **Duration:** {duration:.1f} minutes")
            except Exception:
                pass

        lines.append("")

        # Dependencies
        if experiment.dependencies:
            lines.append("## Dependencies")
            for dep_id in experiment.dependencies:
                dep = self.experiment_store.load(dep_id)
                if dep:
                    lines.append(f"- `{dep_id}` - {dep.title}")
                else:
                    lines.append(f"- `{dep_id}` - Not found")
            lines.append("")

        # Tags
        if experiment.tags:
            lines.append("## Tags")
            for tag in experiment.tags:
                lines.append(f"- `{tag}`")
            lines.append("")

        # Resource requirements
        if experiment.resource_request:
            lines.append("## Resource Requirements")
            for key, value in experiment.resource_request.items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")

        # Worker information
        if experiment.worker_name:
            lines.append("## Execution")
            lines.append(f"- **Worker:** {experiment.worker_name}")
            lines.append(f"- **GPU:** {experiment.gpu_id or 'N/A'}")

            if experiment.pid:
                lines.append(f"- **PID:** {experiment.pid}")

            lines.append("")

        # Results
        if include_results:
            result = self.result_store.load(experiment_id)
            if result:
                lines.extend(self._format_result(result))

        # Config snapshot
        if experiment.config_snapshot:
            lines.append("## Configuration Snapshot")
            lines.append("```yaml")
            lines.append(self._format_dict(experiment.config_snapshot))
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def generate_family_report(
        self,
        family: str,
        include_all: bool = False,
    ) -> str:
        """Generate a markdown report for an experiment family.

        Args:
            family: Family name.
            include_all: Include all experiments (not just completed).

        Returns:
            Markdown report string.
        """
        experiments = self.experiment_store.get_by_family(family)

        if not experiments:
            return f"# Family {family} Not Found\n\nNo experiments in this family."

        lines = [
            f"# Family Report: {family}",
            f"**Total Experiments:** {len(experiments)}",
            "",
            "## Overview",
        ]

        # Status summary
        by_status = {}
        for exp in experiments.values():
            by_status[exp.status] = by_status.get(exp.status, 0) + 1

        for status, count in sorted(by_status.items()):
            lines.append(f"- **{status}:** {count}")

        lines.append("")

        # Best results
        successful_results = {}
        for exp_id, exp in experiments.items():
            if exp.status != "completed":
                continue

            result = self.result_store.load(exp_id)
            if result and result.success:
                successful_results[exp_id] = result

        if successful_results:
            lines.append("## Best Results")

            # Find best for each metric
            all_metrics = set()
            for result in successful_results.values():
                all_metrics.update(result.metrics.keys())

            for metric in sorted(all_metrics):
                best_result = max(
                    successful_results.values(),
                    key=lambda r: float(r.metrics.get(metric, 0)),
                )

                best_exp = experiments[best_result.experiment_id]
                lines.append(
                    f"- **{metric}:** {best_result.metrics[metric]} "
                    f"({best_exp.title}, `{best_exp.id[:12]}`)"
                )

            lines.append("")

        # Experiments list
        lines.append("## Experiments")

        if not include_all:
            experiments = {
                exp_id: exp
                for exp_id, exp in experiments.items()
                if exp.status == "completed"
            }

        sorted_exps = sorted(
            experiments.values(),
            key=lambda e: e.created_at,
        )

        for exp in sorted_exps:
            result = self.result_store.load(exp.id)
            status_icon = "✓" if result and result.success else "✗"

            lines.append(f"### {status_icon} {exp.title}")
            lines.append(f"**ID:** `{exp.id}`")
            lines.append(f"**Status:** {exp.status}")
            lines.append(f"**Created:** {exp.created_at}")

            if result:
                if result.metrics:
                    metrics_str = ", ".join(f"{k}={v}" for k, v in result.metrics.items())
                    lines.append(f"**Metrics:** {metrics_str}")

                if result.summary:
                    lines.append(f"**Summary:** {result.summary}")

            lines.append("")

        return "\n".join(lines)

    def generate_summary_report(self) -> str:
        """Generate a summary report for the entire lab.

        Returns:
            Markdown report string.
        """
        experiments = self.experiment_store.load_all()
        results = self.result_store.load_all()
        hypotheses = self.hypothesis_store.load_all()

        lines = [
            "# Autolab Lab Summary",
            f"**Generated:** {datetime.utcnow().isoformat()}",
            "",
            "## Experiments",
            f"**Total:** {len(experiments)}",
            "",
        ]

        # Status breakdown
        by_status = {}
        for exp in experiments.values():
            by_status[exp.status] = by_status.get(exp.status, 0) + 1

        lines.append("### Status Breakdown")
        for status in ["pending", "ready", "running", "completed", "failed", "blocked", "canceled"]:
            count = by_status.get(status, 0)
            if count > 0:
                icon = self._get_status_icon(status)
                lines.append(f"- {icon} **{status}:** {count}")

        lines.append("")

        # Families
        families = {}
        for exp in experiments.values():
            if exp.family:
                families[exp.family] = families.get(exp.family, 0) + 1

        if families:
            lines.append("### Families")
            sorted_families = sorted(families.items(), key=lambda x: x[1], reverse=True)
            for family, count in sorted_families:
                lines.append(f"- **{family}:** {count}")
            lines.append("")

        # Results
        lines.append("## Results")
        successful = sum(1 for r in results.values() if r.success)
        failed = len(results) - successful

        lines.append(f"**Total:** {len(results)}")
        lines.append(f"- **Successful:** {successful}")
        lines.append(f"- **Failed:** {failed}")

        if successful > 0:
            lines.append("")
            lines.append("### Best Metrics")

            all_metrics = {}
            for result in results.values():
                if result.success:
                    for metric, value in result.metrics.items():
                        if metric not in all_metrics:
                            all_metrics[metric] = []

                        try:
                            all_metrics[metric].append(float(value))
                        except (ValueError, TypeError):
                            pass

            for metric, values in sorted(all_metrics.items()):
                if values:
                    max_val = max(values)
                    max_idx = values.index(max_val)
                    result = [r for r in results.values() if r.success][max_idx]
                    exp = experiments.get(result.experiment_id)
                    exp_name = exp.title if exp else "Unknown"

                    lines.append(f"- **{metric}:** {max_val}")
                    lines.append(f"  - {exp_name} (`{result.experiment_id[:12]}`)")

        lines.append("")

        # Hypotheses
        lines.append("## Hypotheses")
        lines.append(f"**Total:** {len(hypotheses)}")

        by_status = {}
        for hyp in hypotheses.values():
            hyp_status = hyp.get("status", "active")
            by_status[hyp_status] = by_status.get(hyp_status, 0) + 1

        for status, count in sorted(by_status.items()):
            lines.append(f"- **{status}:** {count}")

        lines.append("")

        # Recent activity
        lines.append("## Recent Activity")

        recent_exps = sorted(
            experiments.values(),
            key=lambda e: e.created_at,
            reverse=True,
        )[:10]

        for exp in recent_exps:
            status_icon = self._get_status_icon(exp.status)
            title = exp.title[:40] + "..." if len(exp.title) > 40 else exp.title
            lines.append(f"- {status_icon} `{exp.id[:12]}` {title}")

        lines.append("")

        return "\n".join(lines)

    def _format_result(self, result) -> list[str]:
        """Format result as markdown.

        Args:
            result: Result object.

        Returns:
            List of markdown lines.
        """
        lines = [
            "## Results",
            f"- **Success:** {result.success}",
        ]

        if result.metrics:
            lines.append("")
            lines.append("### Metrics")
            for metric, value in result.metrics.items():
                lines.append(f"- **{metric}:** {value}")

        if result.summary:
            lines.append("")
            lines.append("### Summary")
            lines.append(result.summary)

        if not result.success and result.failure_type:
            lines.append("")
            lines.append("### Failure Analysis")
            lines.append(f"- **Type:** {result.failure_type}")

            if result.failure_reason:
                lines.append(f"- **Reason:** {result.failure_reason}")

        if result.runtime_seconds:
            lines.append("")
            lines.append(f"- **Runtime:** {result.runtime_seconds:.1f}s")

        lines.append("")
        return lines

    def _format_dict(self, data: dict, indent: int = 0) -> str:
        """Format dictionary as YAML-like string.

        Args:
            data: Dictionary to format.
            indent: Indentation level.

        Returns:
            Formatted string.
        """
        lines = []
        prefix = "  " * indent

        for key, value in sorted(data.items()):
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._format_dict(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{prefix}-")
                        lines.append(self._format_dict(item, indent + 2))
                    else:
                        lines.append(f"{prefix}  - {item}")
            else:
                lines.append(f"{prefix}{key}: {value}")

        return "\n".join(lines)

    def _get_status_icon(self, status: str) -> str:
        """Get icon for status.

        Args:
            status: Status string.

        Returns:
            Icon character.
        """
        icons = {
            "pending": "○",
            "ready": "◎",
            "running": "⟳",
            "completed": "✓",
            "failed": "✗",
            "blocked": "⏸",
            "canceled": "−",
        }
        return icons.get(status, "?")
