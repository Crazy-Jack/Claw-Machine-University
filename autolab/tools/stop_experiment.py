"""Tool: stop_experiment

Stop a running experiment.
"""

import argparse
import sys
from pathlib import Path

from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.state_store import StateStore


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Stop a running experiment",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "experiment_id",
        help="ID of experiment to stop",
    )
    parser.add_argument(
        "--workspace",
        default="./autolab_workspace",
        help="Path to workspace directory",
    )
    parser.add_argument(
        "--reason",
        default="Stopped by user",
        help="Reason for stopping",
    )

    args = parser.parse_args()

    # Load data
    workspace_path = Path(args.workspace).expanduser().resolve()
    experiment_store = ExperimentStore(str(workspace_path))
    state_store = StateStore(str(workspace_path))

    # Load experiment
    experiment = experiment_store.load(args.experiment_id)
    if not experiment:
        print(f"Error: Experiment '{args.experiment_id}' not found")
        return 1

    # Check if running
    if experiment.status != "running":
        print(f"Error: Experiment is not running (status: {experiment.status})")
        return 1

    # Update status
    experiment.status = "canceled"
    experiment.finished_at = _now()
    experiment_store.save(experiment)

    # Update state
    state = state_store.load() or state_store._create_default()
    state.last_action = f"stop_experiment:{args.experiment_id}"
    state.last_updated_at = _now()
    state_store.save(state)

    print(f"Stopped experiment {args.experiment_id}")
    print(f"Reason: {args.reason}")
    print(f"Worker: {experiment.worker_name or 'N/A'}")
    print(f"GPU: {experiment.gpu_id or 'N/A'}")

    return 0


def _now():
    """Get current timestamp.

    Returns:
        ISO format timestamp.
    """
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"


if __name__ == "__main__":
    sys.exit(main())
