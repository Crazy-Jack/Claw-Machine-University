"""Tool: mark_baseline

Mark an experiment as a baseline for comparison.
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
        description="Mark an experiment as a baseline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "experiment_id",
        help="ID of experiment to mark as baseline",
    )
    parser.add_argument(
        "--workspace",
        default="./autolab_workspace",
        help="Path to workspace directory",
    )
    parser.add_argument(
        "--family",
        help="Family to mark baseline for (defaults to experiment's family)",
    )
    parser.add_argument(
        "--unmark",
        action="store_true",
        help="Remove baseline mark instead of adding",
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

    # Determine family
    family = args.family or experiment.family
    if not family:
        print("Error: No family specified and experiment has no family")
        return 1

    # Get current state
    state = state_store.load() or state_store._create_default()

    # Update baselines
    if args.unmark:
        if family in state.baselines and state.baselines[family] == args.experiment_id:
            del state.baselines[family]
            print(f"Removed baseline mark for family '{family}'")
        else:
            print(f"Experiment {args.experiment_id} is not baseline for family '{family}'")
            return 1
    else:
        # Check if experiment is completed
        if experiment.status != "completed":
            print(f"Warning: Experiment status is '{experiment.status}', not 'completed'")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != "y":
                return 1

        state.baselines[family] = args.experiment_id
        print(f"Marked experiment {args.experiment_id} as baseline for family '{family}'")
        print(f"Title: {experiment.title}")

    # Save state
    state.last_action = f"mark_baseline:{args.experiment_id}"
    state.last_updated_at = _now()
    state_store.save(state)

    # Show current baselines
    if state.baselines:
        print("\nCurrent baselines:")
        for fam, exp_id in state.baselines.items():
            exp = experiment_store.load(exp_id)
            title = exp.title[:40] + "..." if exp and len(exp.title) > 40 else exp.title if exp else "N/A"
            print(f"  {fam}: {exp_id[:12]} ({title})")

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
