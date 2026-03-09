"""Tool: show_queue

Display current experiment queue.
"""

import argparse
import sys
from pathlib import Path

from autolab.storage.experiment_store import ExperimentStore


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Display current experiment queue",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--workspace",
        default="./autolab_workspace",
        help="Path to workspace directory",
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

    experiments = experiment_store.load_all()

    # Group by status
    by_status = {}
    for exp in experiments.values():
        if exp.status not in by_status:
            by_status[exp.status] = []
        by_status[exp.status].append(exp)

    # Print header
    print(f"Experiment Queue (total: {len(experiments)})")
    print("=" * 80)

    # Print each status category
    for status in ["pending", "ready", "running", "blocked", "completed", "failed", "canceled"]:
        if status not in by_status:
            continue

        exps = sorted(by_status[status], key=lambda e: e.priority, reverse=True)
        print(f"\n{status.upper()} ({len(exps)})")
        print("-" * 80)

        for exp in exps:
            if args.detailed:
                _print_detailed(exp)
            else:
                _print_summary(exp)

    return 0


def _print_summary(experiment):
    """Print summary line for experiment.

    Args:
        experiment: Experiment object.
    """
    title = experiment.title[:50] + "..." if len(experiment.title) > 50 else experiment.title
    print(f"  {experiment.id[:12]} | P:{experiment.priority:5.1f} | {title}")

    if experiment.dependencies:
        deps = ", ".join(experiment.dependencies)
        print(f"    Depends: {deps}")


def _print_detailed(experiment):
    """Print detailed information for experiment.

    Args:
        experiment: Experiment object.
    """
    print(f"  ID: {experiment.id}")
    print(f"  Title: {experiment.title}")
    print(f"  Priority: {experiment.priority}")
    print(f"  Family: {experiment.family or 'N/A'}")
    print(f"  Description: {experiment.description}")

    if experiment.dependencies:
        print(f"  Dependencies: {', '.join(experiment.dependencies)}")

    if experiment.tags:
        print(f"  Tags: {', '.join(experiment.tags)}")

    if experiment.worker_name:
        print(f"  Worker: {experiment.worker_name}")
        print(f"  GPU: {experiment.gpu_id or 'N/A'}")

    print(f"  Created: {experiment.created_at}")


if __name__ == "__main__":
    sys.exit(main())
