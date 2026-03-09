"""Tool: list_failures

List failed experiments with failure analysis.
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.result_store import ResultStore


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="List failed experiments with failure analysis",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--workspace",
        default="./autolab_workspace",
        help="Path to workspace directory",
    )
    parser.add_argument(
        "--failure-type",
        help="Filter by specific failure type",
    )
    parser.add_argument(
        "--group-by",
        choices=["family", "type", "resource"],
        help="Group failures by category",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of failures to show",
    )

    args = parser.parse_args()

    # Load data
    workspace_path = Path(args.workspace).expanduser().resolve()
    experiment_store = ExperimentStore(str(workspace_path))
    result_store = ResultStore(str(workspace_path))

    experiments = experiment_store.load_all()
    results = result_store.load_all()

    # Find failed experiments
    failed_results = {exp_id: result for exp_id, result in results.items() if not result.success}

    # Filter by failure type if specified
    if args.failure_type:
        failed_results = {
            exp_id: result
            for exp_id, result in failed_results.items()
            if result.failure_type == args.failure_type
        }

    if not failed_results:
        print("No failed experiments found matching criteria.")
        return 0

    # Print summary
    print(f"Failed Experiments (total: {len(failed_results)})")
    print("=" * 80)

    # Group failures if requested
    if args.group_by == "type":
        _group_by_type(failed_results, experiments)
    elif args.group_by == "family":
        _group_by_family(failed_results, experiments)
    elif args.group_by == "resource":
        _group_by_resource(failed_results, experiments)
    else:
        _list_failures(failed_results, experiments, args.limit)

    return 0


def _group_by_type(failed_results, experiments):
    """Group failures by type.

    Args:
        failed_results: Dictionary of failed results.
        experiments: All experiments.
    """
    # Count by failure type
    type_counts = Counter()
    for result in failed_results.values():
        if result.failure_type:
            type_counts[result.failure_type] += 1
        else:
            type_counts["unknown"] += 1

    print("\nFailure Types:")
    print("-" * 80)
    for failure_type, count in type_counts.most_common():
        print(f"  {failure_type}: {count}")

    # List failures by type
    for failure_type, _ in type_counts.most_common():
        print(f"\n{failure_type.upper()}:")
        print("-" * 80)

        for exp_id, result in failed_results.items():
            if result.failure_type != failure_type:
                continue

            exp = experiments.get(exp_id)
            if exp:
                title = exp.title[:50] + "..." if len(exp.title) > 50 else exp.title
                print(f"  {exp_id[:12]} | {exp.family or 'N/A':15} | {title}")

            if result.failure_reason:
                print(f"    Reason: {result.failure_reason[:100]}")


def _group_by_family(failed_results, experiments):
    """Group failures by family.

    Args:
        failed_results: Dictionary of failed results.
        experiments: All experiments.
    """
    # Group by family
    family_failures = {}
    for exp_id in failed_results.keys():
        exp = experiments.get(exp_id)
        family = exp.family if exp else "unknown"

        if family not in family_failures:
            family_failures[family] = []

        family_failures[family].append(exp_id)

    # Sort by number of failures
    sorted_families = sorted(family_failures.items(), key=lambda x: len(x[1]), reverse=True)

    print("\nFailures by Family:")
    print("-" * 80)

    for family, exp_ids in sorted_families:
        print(f"\n{family or 'N/A'} ({len(exp_ids)} failures):")

        for exp_id in exp_ids:
            result = failed_results[exp_id]
            exp = experiments.get(exp_id)

            if exp:
                title = exp.title[:50] + "..." if len(exp.title) > 50 else exp.title
                print(f"  {exp_id[:12]} | {title}")

            failure_info = result.failure_type or "unknown"
            print(f"    Failure: {failure_info}")


def _group_by_resource(failed_results, experiments):
    """Group failures by resource requirements.

    Args:
        failed_results: Dictionary of failed results.
        experiments: All experiments.
    """
    # Group by worker/GPU
    worker_failures = {}
    gpu_failures = {}

    for exp_id in failed_results.keys():
        exp = experiments.get(exp_id)
        if not exp:
            continue

        if exp.worker_name:
            worker_failures[exp.worker_name] = worker_failures.get(exp.worker_name, 0) + 1

        if exp.gpu_id:
            gpu_failures[exp.gpu_id] = gpu_failures.get(exp.gpu_id, 0) + 1

    print("\nFailures by Worker:")
    print("-" * 80)
    for worker, count in sorted(worker_failures.items(), key=lambda x: x[1], reverse=True):
        print(f"  {worker}: {count}")

    print("\nFailures by GPU:")
    print("-" * 80)
    for gpu, count in sorted(gpu_failures.items(), key=lambda x: x[1], reverse=True):
        print(f"  {gpu}: {count}")


def _list_failures(failed_results, experiments, limit):
    """List all failures.

    Args:
        failed_results: Dictionary of failed results.
        experiments: All experiments.
        limit: Maximum number to show.
    """
    # Sort by creation time
    sorted_results = sorted(
        failed_results.items(),
        key=lambda x: x[1].created_at,
        reverse=True,
    )[:limit]

    for exp_id, result in sorted_results:
        exp = experiments.get(exp_id)

        print(f"\n{exp_id}")
        print("-" * 80)

        if exp:
            print(f"  Title: {exp.title}")
            print(f"  Family: {exp.family or 'N/A'}")
            print(f"  Worker: {exp.worker_name or 'N/A'}")
            print(f"  GPU: {exp.gpu_id or 'N/A'}")

        print(f"  Failure Type: {result.failure_type or 'unknown'}")

        if result.failure_reason:
            print(f"  Reason: {result.failure_reason}")

        if result.metrics:
            print(f"  Metrics: {result.metrics}")

        if result.summary:
            print(f"  Summary: {result.summary}")


if __name__ == "__main__":
    sys.exit(main())
