"""OpenClaw skill: autolab_generate_report

Generate reports for experiments, results, and cycles.
"""

from datetime import datetime
from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.result_store import ResultStore
from autolab.storage.hypothesis_store import HypothesisStore


def execute(args: dict) -> dict:
    """Execute generate_report skill.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with report generation results.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    report_type = args.get("report_type", "experiments")  # experiments, cycle, summary
    experiment_ids = args.get("experiment_ids", [])  # Optional: specific experiments
    cycle_number = args.get("cycle_number")  # Optional: cycle number for cycle report

    # Load data
    experiment_store = ExperimentStore(workspace_path)
    result_store = ResultStore(workspace_path)
    hypothesis_store = HypothesisStore(workspace_path)

    experiments = experiment_store.load_all()
    results = result_store.load_all()
    hypotheses = hypothesis_store.load_all()

    if report_type == "cycle" and cycle_number:
        report = _generate_cycle_report(
            experiments,
            results,
            hypotheses,
            cycle_number,
        )
    elif experiment_ids:
        report = _generate_experiment_report(
            experiments,
            results,
            experiment_ids,
        )
    else:
        report = _generate_summary_report(
            experiments,
            results,
            hypotheses,
        )

    # Save report
    report_path = _save_report(report, report_type, workspace_path)

    return {
        "success": True,
        "report": report,
        "report_path": report_path,
        "report_type": report_type,
    }


def _generate_summary_report(
    experiments: dict,
    results: dict,
    hypotheses: dict,
) -> str:
    """Generate a summary report.

    Args:
        experiments: All experiments.
        results: All results.
        hypotheses: All hypotheses.

    Returns:
        Markdown report string.
    """
    lines = [
        "# Autolab Summary Report",
        f"Generated: {datetime.utcnow().isoformat()}",
        "",
    ]

    # Experiments summary
    lines.append("## Experiments Summary")
    lines.append(f"Total experiments: {len(experiments)}")

    by_status = {}
    for exp in experiments.values():
        by_status[exp.status] = by_status.get(exp.status, 0) + 1

    for status, count in sorted(by_status.items()):
        lines.append(f"- {status}: {count}")

    lines.append("")

    # Results summary
    lines.append("## Results Summary")
    successful = sum(1 for r in results.values() if r.success)
    failed = len(results) - successful
    lines.append(f"Total results: {len(results)}")
    lines.append(f"- Successful: {successful}")
    lines.append(f"- Failed: {failed}")

    if successful > 0:
        lines.append("")
        lines.append("### Best Metrics")

        # Collect all metrics
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
                lines.append(f"- {metric}: max={max(values):.4f}, min={min(values):.4f}, avg={sum(values)/len(values):.4f}")

    lines.append("")

    # Hypotheses summary
    lines.append("## Hypotheses Summary")
    lines.append(f"Total hypotheses: {len(hypotheses)}")

    by_status = {}
    for hyp in hypotheses.values():
        hyp_status = hyp.get("status", "active")
        by_status[hyp_status] = by_status.get(hyp_status, 0) + 1

    for status, count in sorted(by_status.items()):
        lines.append(f"- {status}: {count}")

    lines.append("")

    return "\n".join(lines)


def _generate_experiment_report(
    experiments: dict,
    results: dict,
    experiment_ids: list[str],
) -> str:
    """Generate a report for specific experiments.

    Args:
        experiments: All experiments.
        results: All results.
        experiment_ids: Experiment IDs to include.

    Returns:
        Markdown report string.
    """
    lines = [
        "# Experiment Report",
        f"Generated: {datetime.utcnow().isoformat()}",
        "",
    ]

    for exp_id in experiment_ids:
        experiment = experiments.get(exp_id)
        if not experiment:
            lines.append(f"## Experiment {exp_id} - NOT FOUND")
            lines.append("")
            continue

        lines.append(f"## Experiment: {experiment.title}")
        lines.append(f"ID: {experiment.id}")
        lines.append(f"Status: {experiment.status}")
        lines.append(f"Family: {experiment.family or 'N/A'}")
        lines.append(f"Description: {experiment.description}")
        lines.append(f"Objective: {experiment.objective}")
        lines.append(f"Priority: {experiment.priority}")
        lines.append(f"Created: {experiment.created_at}")

        if experiment.started_at:
            lines.append(f"Started: {experiment.started_at}")

        if experiment.finished_at:
            lines.append(f"Finished: {experiment.finished_at}")

        if experiment.worker_name:
            lines.append(f"Worker: {experiment.worker_name}")
            lines.append(f"GPU: {experiment.gpu_id or 'N/A'}")

        lines.append("")

        # Result info
        result = results.get(exp_id)
        if result:
            lines.append("### Results")
            lines.append(f"Success: {result.success}")

            if result.metrics:
                lines.append("Metrics:")
                for metric, value in result.metrics.items():
                    lines.append(f"- {metric}: {value}")

            if result.summary:
                lines.append("")
                lines.append(f"Summary: {result.summary}")

            if not result.success and result.failure_type:
                lines.append("")
                lines.append(f"Failure Type: {result.failure_type}")
                if result.failure_reason:
                    lines.append(f"Failure Reason: {result.failure_reason}")

        lines.append("")

    return "\n".join(lines)


def _generate_cycle_report(
    experiments: dict,
    results: dict,
    hypotheses: dict,
    cycle_number: int,
) -> str:
    """Generate a report for a specific cycle.

    Args:
        experiments: All experiments.
        results: All results.
        hypotheses: All hypotheses.
        cycle_number: Cycle number.

    Returns:
        Markdown report string.
    """
    lines = [
        f"# Cycle {cycle_number} Report",
        f"Generated: {datetime.utcnow().isoformat()}",
        "",
    ]

    # For now, generate a simple report
    lines.append("## Cycle Summary")
    lines.append("Detailed cycle tracking to be implemented in Phase 3")
    lines.append("")

    # Show recent experiments
    lines.append("## Recent Experiments")

    recent_exps = sorted(
        experiments.values(),
        key=lambda e: e.created_at,
        reverse=True,
    )[:10]

    for exp in recent_exps:
        lines.append(f"- {exp.id}: {exp.title} ({exp.status})")

    lines.append("")

    # Show recent results
    lines.append("## Recent Results")

    recent_results = sorted(
        results.values(),
        key=lambda r: r.created_at,
        reverse=True,
    )[:10]

    for result in recent_results:
        exp = experiments.get(result.experiment_id)
        title = exp.title if exp else "Unknown"
        status = "✓" if result.success else "✗"
        lines.append(f"- {status} {result.experiment_id}: {title}")

        if result.metrics:
            metric_str = ", ".join(f"{k}={v}" for k, v in result.metrics.items())
            lines.append(f"  {metric_str}")

    lines.append("")

    return "\n".join(lines)


def _save_report(report: str, report_type: str, workspace_path: str) -> str:
    """Save report to file.

    Args:
        report: Report content.
        report_type: Type of report.
        workspace_path: Workspace path.

    Returns:
        Path to saved report.
    """
    from pathlib import Path

    reports_dir = Path(workspace_path) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{report_type}_{timestamp}.md"
    report_path = reports_dir / filename

    with open(report_path, "w") as f:
        f.write(report)

    return str(report_path)


def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Skill specification dictionary.
    """
    return {
        "name": "autolab_generate_report",
        "description": "Generate reports for experiments, results, and cycles",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "Path to autolab workspace",
                    "default": "./autolab_workspace",
                },
                "report_type": {
                    "type": "string",
                    "description": "Type of report (experiments, cycle, summary)",
                    "default": "experiments",
                    "enum": ["experiments", "cycle", "summary"],
                },
                "experiment_ids": {
                    "type": "array",
                    "description": "List of experiment IDs for experiments report",
                    "items": {"type": "string"},
                },
                "cycle_number": {
                    "type": "integer",
                    "description": "Cycle number for cycle report",
                },
            },
            "required": [],
        },
    }
