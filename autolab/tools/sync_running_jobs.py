"""Tool: sync_running_jobs

Synchronize status of running jobs with workers.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.state_store import StateStore
from autolab.executor.worker_registry import WorkerRegistry


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Sync running jobs with worker status",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--workspace",
        default="./autolab_workspace",
        help="Path to workspace directory",
    )
    parser.add_argument(
        "--cancel-lost",
        action="store_true",
        help="Cancel jobs that no longer exist on workers",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    # Load data
    workspace_path = Path(args.workspace).expanduser().resolve()
    experiment_store = ExperimentStore(str(workspace_path))
    state_store = StateStore(str(workspace_path))
    worker_registry = WorkerRegistry(str(workspace_path))

    # Get running experiments
    experiments = experiment_store.load_all()
    running_exps = {
        exp_id: exp
        for exp_id, exp in experiments.items()
        if exp.status == "running"
    }

    if not running_exps:
        print("No running experiments found")
        return 0

    print(f"Found {len(running_exps)} running experiment(s)")

    # Get worker status
    workers = worker_registry.get_all_workers()
    print(f"Found {len(workers)} worker(s)")

    # Track changes
    updates = []
    lost = []

    # Check each running experiment
    for exp_id, exp in running_exps.items():
        if not exp.worker_name:
            print(f"\n{exp_id[:12]}: No worker assigned")
            lost.append(exp_id)
            continue

        # Find worker
        worker = None
        for w in workers:
            if w.name == exp.worker_name:
                worker = w
                break

        if not worker:
            print(f"\n{exp_id[:12]}: Worker '{exp.worker_name}' not found")
            lost.append(exp_id)
            continue

        # Check if job exists on worker
        job_exists = False
        for job in worker.active_jobs:
            if job.get("experiment_id") == exp_id:
                job_exists = True
                break

        if job_exists:
            print(f"\n{exp_id[:12]}: Running on {worker.name}")
        else:
            print(f"\n{exp_id[:12]}: Job not found on {worker.name}")
            lost.append(exp_id)

    # Apply changes
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - no changes made")
        if lost:
            print(f"\nWould mark {len(lost)} experiment(s) as failed:")
            for exp_id in lost:
                print(f"  {exp_id[:12]}")
    elif lost and args.cancel_lost:
        print("\n" + "=" * 60)
        print(f"Marking {len(lost)} experiment(s) as failed...")

        for exp_id in lost:
            exp = running_exps[exp_id]
            exp.status = "failed"
            exp.finished_at = _now()
            experiment_store.save(exp)
            updates.append(exp_id)
            print(f"  {exp_id[:12]}: {exp.title[:40]}")

        # Update state
        if updates:
            state = state_store.load() or state_store._create_default()
            state.last_action = f"sync_running_jobs:failed={len(updates)}"
            state.last_updated_at = _now()
            state_store.save(state)

        print(f"\nUpdated {len(updates)} experiment(s)")
    elif lost:
        print("\n" + "=" * 60)
        print(f"Found {len(lost)} lost experiment(s)")
        print("Use --cancel-lost to mark them as failed")

    return 0


def _now():
    """Get current timestamp.

    Returns:
        ISO format timestamp.
    """
    return datetime.utcnow().isoformat() + "Z"


if __name__ == "__main__":
    sys.exit(main())
