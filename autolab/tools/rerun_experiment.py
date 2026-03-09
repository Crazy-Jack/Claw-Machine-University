"""Tool: rerun_experiment

Rerun a failed or canceled experiment.
"""

import argparse
import sys
import uuid
from pathlib import Path
from datetime import datetime

from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.state_store import StateStore


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Rerun a failed or canceled experiment",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "experiment_id",
        help="ID of experiment to rerun",
    )
    parser.add_argument(
        "--workspace",
        default="./autolab_workspace",
        help="Path to workspace directory",
    )
    parser.add_argument(
        "--priority",
        type=float,
        help="New priority for rerun experiment",
    )
    parser.add_argument(
        "--increment",
        type=int,
        default=1,
        help="Add this to priority (default: +1)",
    )
    parser.add_argument(
        "--keep-original",
        action="store_true",
        help="Keep original experiment in history",
    )

    args = parser.parse_args()

    # Load data
    workspace_path = Path(args.workspace).expanduser().resolve()
    experiment_store = ExperimentStore(str(workspace_path))
    state_store = StateStore(str(workspace_path))

    # Load original experiment
    original = experiment_store.load(args.experiment_id)
    if not original:
        print(f"Error: Experiment '{args.experiment_id}' not found")
        return 1

    # Check if experiment is failed or canceled
    if original.status not in ["failed", "canceled"]:
        print(f"Error: Experiment status is '{original.status}', can only rerun failed/canceled experiments")
        return 1

    print(f"Rerunning experiment: {original.title}")
    print(f"Original ID: {args.experiment_id}")
    print(f"Original status: {original.status}")
    print(f"Original family: {original.family or 'N/A'}")

    # Determine new priority
    if args.priority is not None:
        new_priority = args.priority
    else:
        new_priority = original.priority + args.increment

    # Create new experiment
    new_exp = original.copy(update={
        "id": str(uuid.uuid4()),
        "status": "pending",
        "priority": new_priority,
        "created_at": _now(),
        "started_at": None,
        "finished_at": None,
        "worker_name": None,
        "gpu_id": None,
        "tags": (original.tags or []) + ["rerun"],
        "retry_of": args.experiment_id,
    })

    # Update title
    new_exp.title = f"[Rerun] {original.title}"

    # Save new experiment
    experiment_store.save(new_exp)

    # Update original if not keeping
    if not args.keep_original:
        # Keep as reference but don't delete
        pass

    # Update state
    state = state_store.load() or state_store._create_default()
    state.last_action = f"rerun_experiment:{args.experiment_id}->{new_exp.id}"
    state.last_updated_at = _now()
    state_store.save(state)

    print(f"\nNew experiment created:")
    print(f"  ID: {new_exp.id}")
    print(f"  Title: {new_exp.title}")
    print(f"  Priority: {original.priority} -> {new_priority}")

    return 0


def _now():
    """Get current timestamp.

    Returns:
        ISO format timestamp.
    """
    return datetime.utcnow().isoformat() + "Z"


if __name__ == "__main__":
    sys.exit(main())
