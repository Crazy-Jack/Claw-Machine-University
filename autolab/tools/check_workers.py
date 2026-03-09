"""Tool: check_workers

Check health and status of workers.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

from autolab.executor.worker_registry import WorkerRegistry


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Check worker health and status",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--workspace",
        default="./autolab_workspace",
        help="Path to workspace directory",
    )
    parser.add_argument(
        "--worker",
        help="Check specific worker only",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update worker status (SSH connection check)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed information",
    )

    args = parser.parse_args()

    # Load worker registry
    workspace_path = Path(args.workspace).expanduser().resolve()
    worker_registry = WorkerRegistry(str(workspace_path))

    # Get workers
    if args.worker:
        workers = [worker_registry.get_worker(args.worker)]
        if not workers or not workers[0]:
            print(f"Error: Worker '{args.worker}' not found")
            return 1
    else:
        workers = worker_registry.get_all_workers()

    if not workers:
        print("No workers registered")
        return 0

    print(f"Checking {len(workers)} worker(s)")
    print("=" * 80)

    # Check each worker
    issues = []
    for worker in workers:
        _print_worker(worker, args.verbose, args.update)

        # Check for issues
        if worker.status != "available":
            issues.append((worker.name, worker.status))

    # Print summary
    print("\n" + "=" * 80)
    print("Summary:")
    print(f"  Total workers: {len(workers)}")
    print(f"  Available: {sum(1 for w in workers if w.status == 'available')}")
    print(f"  Busy: {sum(1 for w in workers if w.status == 'busy')}")
    print(f"  Offline: {sum(1 for w in workers if w.status == 'offline')}")
    print(f"  Total GPUs: {sum(len(w.gpus) for w in workers)}")

    if issues:
        print("\nIssues found:")
        for name, status in issues:
            print(f"  {name}: {status}")
        return 1

    return 0


def _print_worker(worker, verbose, update):
    """Print worker information.

    Args:
        worker: Worker object.
        verbose: Show detailed info.
        update: Update worker status.
    """
    status_icon = _get_status_icon(worker.status)
    print(f"\n{status_icon} {worker.name} ({worker.status})")

    print(f"  Host: {worker.host}:{worker.port}")
    print(f"  Username: {worker.username}")
    print(f"  GPUs: {len(worker.gpus)}")

    if worker.gpus:
        for i, gpu in enumerate(worker.gpus):
            print(f"    GPU {i}: {gpu.name} ({gpu.memory_gb}GB) - {gpu.status}")

    if worker.active_jobs:
        print(f"  Active jobs: {len(worker.active_jobs)}")
        for job in worker.active_jobs:
            exp_id = job.get("experiment_id", "unknown")[:12]
            print(f"    {exp_id}: {job.get('status', 'unknown')}")

    if verbose:
        print(f"\n  Last seen: {worker.last_seen}")
        print(f"  Last updated: {worker.last_updated}")
        print(f"  Work directory: {worker.work_dir}")
        if worker.gpus:
            print(f"  GPU command: {worker.gpu_command}")

    # Update status if requested
    if update:
        print(f"\n  Updating status...")


def _get_status_icon(status):
    """Get icon for status.

    Args:
        status: Status string.

    Returns:
        Icon character.
    """
    icons = {
        "available": "✓",
        "busy": "⟳",
        "offline": "✗",
    }
    return icons.get(status, "?")


if __name__ == "__main__":
    sys.exit(main())
