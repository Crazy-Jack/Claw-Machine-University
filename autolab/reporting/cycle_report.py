"""Cycle report generator for Autolab."""

from datetime import datetime
from pathlib import Path
from typing import Any

from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.result_store import ResultStore
from autolab.storage.hypothesis_store import HypothesisStore


class CycleReportGenerator:
    """Generate cycle reports for Autolab."""

    def __init__(self, workspace_path: str = "./autolab_workspace") -> None:
        """Initialize cycle report generator.

        Args:
            workspace_path: Path to workspace directory.
        """
        self.workspace_path = Path(workspace_path).expanduser().resolve()
        self.reports_dir = self.workspace_path / "reports" / "cycles"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.experiment_store = ExperimentStore(str(self.workspace_path))
        self.result_store = ResultStore(str(self.workspace_path))
        self.hypothesis_store = HypothesisStore(str(self.workspace_path))

    def generate_cycle_report(
        self,
        cycle_number: int,
        cycle_start_time: str,
        cycle_end_time: str,
        actions_applied: list[dict[str, Any]],
        experiments_launched: list[str],
        experiments_completed: list[str],
        errors: list[str],
    ) -> str:
        """Generate a markdown report for a single cycle.

        Args:
            cycle_number: Cycle number.
            cycle_start_time: ISO timestamp of cycle start.
            cycle_end_time: ISO timestamp of cycle end.
            actions_applied: List of actions applied in this cycle.
            experiments_launched: List of experiment IDs launched.
            experiments_completed: List of experiment IDs completed.
            errors: List of errors encountered.

        Returns:
            Markdown report string.
        """
        # Calculate duration
        start = datetime.fromisoformat(cycle_start_time.replace("Z", ""))
        end = datetime.fromisoformat(cycle_end_time.replace("Z", ""))
        duration = (end - start).total_seconds()

        lines = [
            f"# Cycle {cycle_number} Report",
            "",
            "## Cycle Information",
            f"- **Start:** {cycle_start_time}",
            f"- **End:** {cycle_end_time}",
            f"- **Duration:** {duration:.1f}s",
            "",
        ]

        # Actions applied
        if actions_applied:
            lines.append("## Actions Applied")
            lines.append(f"**Total:** {len(actions_applied)}")

            for i, action in enumerate(actions_applied, 1):
                action_type = action.get("action_type", "unknown")
                lines.append(f"### {i}. {action_type}")

                if action.get("rationale"):
                    lines.append(f"**Rationale:** {action['rationale']}")

                if action.get("payload"):
                    lines.append("**Payload:**")
                    lines.append("```json")
                    lines.append(self._format_dict(action["payload"]))
                    lines.append("```")

                lines.append("")

        # Experiments launched
        if experiments_launched:
            lines.append("## Experiments Launched")
            lines.append(f"**Total:** {len(experiments_launched)}")

            for exp_id in experiments_launched:
                exp = self.experiment_store.load(exp_id)
                if exp:
                    lines.append(f"- `{exp_id}` - {exp.title}")
                else:
                    lines.append(f"- `{exp_id}` - Not found")

            lines.append("")

        # Experiments completed
        if experiments_completed:
            lines.append("## Experiments Completed")
            lines.append(f"**Total:** {len(experiments_completed)}")

            successful_count = 0
            failed_count = 0

            for exp_id in experiments_completed:
                result = self.result_store.load(exp_id)
                exp = self.experiment_store.load(exp_id)

                status = "✓" if result and result.success else "✗"
                if result and result.success:
                    successful_count += 1
                else:
                    failed_count += 1

                if exp:
                    lines.append(f"- {status} `{exp_id}` - {exp.title}")
                else:
                    lines.append(f"- {status} `{exp_id}` - Not found")

            lines.append("")
            lines.append(f"**Successful:** {successful_count}")
            lines.append(f"**Failed:** {failed_count}")
            lines.append("")

        # Errors
        if errors:
            lines.append("## Errors")
            lines.append(f"**Total:** {len(errors)}")

            for error in errors:
                lines.append(f"- {error}")

            lines.append("")

        # Cycle metrics
        lines.append("## Cycle Metrics")

        # Count experiments by status
        all_experiments = self.experiment_store.load_all()
        by_status = {}
        for exp in all_experiments.values():
            by_status[exp.status] = by_status.get(exp.status, 0) + 1

        for status in ["pending", "ready", "running", "completed", "failed", "blocked"]:
            count = by_status.get(status, 0)
            if count > 0 or status in ["pending", "ready", "running"]:
                lines.append(f"- **{status}:** {count}")

        lines.append("")

        # Hypotheses
        hypotheses = self.hypothesis_store.load_all()
        active_hyps = sum(1 for h in hypotheses.values() if h.get("status") == "active")
        lines.append(f"**Active Hypotheses:** {active_hyps}")
        lines.append("")

        return "\n".join(lines)

    def generate_periodic_report(
        self,
        start_cycle: int,
        end_cycle: int,
    ) -> str:
        """Generate a periodic report spanning multiple cycles.

        Args:
            start_cycle: Starting cycle number.
            end_cycle: Ending cycle number.

        Returns:
            Markdown report string.
        """
        lines = [
            f"# Periodic Report: Cycles {start_cycle}-{end_cycle}",
            "",
            "## Summary",
            f"**Cycles:** {end_cycle - start_cycle + 1}",
            f"**Generated:** {datetime.utcnow().isoformat()}",
            "",
        ]

        # Collect data from all cycles
        total_actions = 0
        total_launched = 0
        total_completed = 0
        total_successful = 0

        for cycle_num in range(start_cycle, end_cycle + 1):
            report_path = self.reports_dir / f"cycle_{cycle_num}.md"

            if not report_path.exists():
                continue

            with open(report_path) as f:
                content = f.read()

            # Parse basic metrics
            if "Actions Applied" in content:
                actions_line = [line for line in content.split("\n") if "Total:" in line and line.startswith("**Total:**")]
                if actions_line:
                    try:
                        total = int(actions_line[0].split(":")[1].strip())
                        total_actions += total
                    except (ValueError, IndexError):
                        pass

            if "Experiments Launched" in content:
                lines = content.split("\n")
                for line in lines:
                    if line.startswith("**Total:**"):
                        try:
                            total = int(line.split(":")[1].strip())
                            total_launched += total
                        except (ValueError, IndexError):
                            pass
                        break

            if "Experiments Completed" in content:
                lines = content.split("\n")
                for line in lines:
                    if "**Successful:**" in line:
                        try:
                            total = int(line.split(":")[1].strip())
                            total_successful += total
                        except (ValueError, IndexError):
                            pass
                    if line.startswith("**Failed:**") or line.startswith("**Successful:**"):
                        try:
                            total = int(line.split(":")[1].strip())
                            total_completed += total
                        except (ValueError, IndexError):
                            pass

        lines.append("### Totals")
        lines.append(f"- **Actions Applied:** {total_actions}")
        lines.append(f"- **Experiments Launched:** {total_launched}")
        lines.append(f"- **Experiments Completed:** {total_completed}")
        lines.append(f"- **Successful:** {total_successful}")
        lines.append(f"- **Failed:** {total_completed - total_successful}")
        lines.append("")

        # Best results across period
        lines.append("## Best Results")

        all_experiments = self.experiment_store.load_all()
        all_results = self.result_store.load_all()

        successful_results = {
            exp_id: result
            for exp_id, result in all_results.items()
            if result.success
        }

        if successful_results:
            all_metrics = set()
            for result in successful_results.values():
                all_metrics.update(result.metrics.keys())

            for metric in sorted(all_metrics):
                best_result = max(
                    successful_results.values(),
                    key=lambda r: float(r.metrics.get(metric, 0)),
                )

                best_exp = all_experiments.get(best_result.experiment_id)
                exp_name = best_exp.title if best_exp else "Unknown"

                lines.append(f"- **{metric}:** {best_result.metrics[metric]}")
                lines.append(f"  - {exp_name} (`{best_result.experiment_id[:12]}`)")

        lines.append("")

        # Failure analysis
        lines.append("## Failure Analysis")

        failed_results = {
            exp_id: result
            for exp_id, result in all_results.items()
            if not result.success
        }

        if failed_results:
            from collections import Counter

            failure_types = Counter()
            for result in failed_results.values():
                if result.failure_type:
                    failure_types[result.failure_type] += 1

            for failure_type, count in failure_types.most_common():
                lines.append(f"- **{failure_type}:** {count}")

        else:
            lines.append("No failures in this period.")

        lines.append("")

        return "\n".join(lines)

    def save_report(self, cycle_number: int, content: str) -> Path:
        """Save cycle report to file.

        Args:
            cycle_number: Cycle number.
            content: Report content.

        Returns:
            Path to saved report.
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        filename = f"cycle_{cycle_number}_{timestamp}.md"
        report_path = self.reports_dir / filename

        with open(report_path, "w") as f:
            f.write(content)

        return report_path

    def load_report(self, cycle_number: int) -> str | None:
        """Load cycle report from file.

        Args:
            cycle_number: Cycle number.

        Returns:
            Report content or None if not found.
        """
        report_path = self.reports_dir / f"cycle_{cycle_number}.md"

        if not report_path.exists():
            return None

        with open(report_path) as f:
            return f.read()

    def list_cycles(self) -> list[int]:
        """List all available cycle reports.

        Returns:
            List of cycle numbers.
        """
        cycles = []

        for file in self.reports_dir.glob("cycle_*.md"):
            try:
                # Extract cycle number from filename
                # Format: cycle_<number>_<timestamp>.md or cycle_<number>.md
                name = file.stem
                parts = name.split("_")

                if len(parts) >= 2:
                    cycle_num = int(parts[1])
                    cycles.append(cycle_num)
            except (ValueError, IndexError):
                continue

        return sorted(cycles)

    def _format_dict(self, data: dict, indent: int = 0) -> str:
        """Format dictionary as JSON-like string.

        Args:
            data: Dictionary to format.
            indent: Indentation level.

        Returns:
            Formatted string.
        """
        import json

        return json.dumps(data, indent=2)
