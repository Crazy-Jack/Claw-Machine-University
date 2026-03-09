"""Tool: show_history

Display experiment history.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.result_store import ResultStore


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Display experiment history",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--workspace",
        default="./autolab_workspace",
        help="Path to workspace directory",
    )
    parser.add_argument(
        "--status",
        choices=["pending", "ready", "running", "completed", "failed", "blocked", "canceled"],
        help="Filter by status",
    )
    parser.add_argument(
        "--family",
        help="Filter by family",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of experiments to show",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed information",
    )

    args = parser.parse_args()

    # Load data
    workspace_path = Path(args.workspace).expanduser().resolve()
    experiment_store = ExperimentStore(str(workspace_path))
    result_store = ResultStore(str(workspace_path))

    experiments = experiment_store.load_all()
    results = result_store.load_all()

    # Filter experiments
    filtered = {}
    for exp_id, exp in experiments.items():
        if args.status and exp.status != args.status:
            continue
        if args.family and exp.family != args.family:
            continue
        filtered[exp_id] = exp

    # Sort by creation time
    sorted_exps = sorted(
        filtered.values(),
        key=lambda e: e.created_at,
        reverse=True,
    )[: args.limit]

    # Print header
    print(f"Experiment History (showing {len(sorted_exps)}/{len(experiments)} total)")
    print("=" * 80)

    if not sorted_exps:
        print("No experiments found matching criteria.")
        return 0

    # Print experiments
    for exp in sorted_exps:
        if args.detailed:
            _print_detailed(exp, results.get(exp.id))
        else:
            _print_summary(exp, results.get(exp.id))
        print("-" * 80)

    return 0


def _print_summary(experiment, result):
    """Print summary line for experiment.

    Args:
        experiment: Experiment object.
        result: Result object or None.
    """
    status_icon = _get_status_icon(experiment.status)
    title = experiment.title[:50] + "..." if len(experiment.title) > 50 else experiment.title

    print(f"{status_icon} {experiment.id[:12]} | {experiment.status:12} | {title}")

    if experiment.family:
        print(f"   Family: {experiment.family}")

    if result:
        metrics_str = ", ".join(f"{k}={v}" for k, v in result.metrics.items())
        print(f"   Metrics: {metrics_str}")


def _print_detailed(experiment, result):
    """Print detailed information for experiment.

    Args:
        experiment: Experiment object.
        result: Result object or None.
    """
    print(f"ID: {experiment.id}")
    print(f"Title: {experiment.title}")
    print(f"Status: {experiment.status}")
    print(f"Family: {experiment.family or 'N/A'}")
    print(f"Description: {experiment.description}")
    print(f"Objective: {experiment.objective}")
    print(f"Priority: {experiment.priority}")
    print(f"Created: {experiment.created_at}")

    if experiment.started_at:
        print(f"Started: {experiment.started_at}")

    if experiment.finished_at:
        print(f"Finished: {experiment.finished_at}")
        if experiment.started_at:
            started = datetime.fromisoformat(experiment.started_at.replace("Z", ""))
            finished = datetime.fromisoformat(experiment.finished_at.replace("Z", ""))
            duration = (finished - started).total_seconds() / 60
            print(f"Duration: {duration:.1f} minutes")

    if experiment.worker_name:
        print(f"Worker: {experiment.worker_name}")
        print(f"GPU: {experiment.gpu_id or 'N/A'}")

    if experiment.dependencies:
        print(f"Dependencies: {', '.join(experiment.dependencies)}")

    if experiment.tags:
        print(f"Tags: {', '.join(experiment.tags)}")

    if result:
        print("")
        print("Results:")
        print(f"  Success: {result.success}")
        if result.metrics:
            print("  Metrics:")
            for metric, value in result.metrics.items():
                print(f"    {metric}: {value}")
        if result.summary:
            print(f"  Summary: {result.summary}")
        if not result.success and result.failure_type:
            print(f"  Failure Type: {result.failure_type}")
            if result.failure_reason:
                print(f"  Failure Reason: {result.failure_reason}")
        if result.runtime_seconds:
            print(f"  Runtime: {result.runtime_seconds:.1f}s")


def _get_status_icon(status):
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


if __name__ == "__main__":
    sys.exit(main())
