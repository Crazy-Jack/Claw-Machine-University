"""Tool: rebuild_state

Rebuild state store from experiment and result data.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.result_store import ResultStore
from autolab.storage.state_store import StateStore
from autolab.schemas.experiment import ExperimentStatus


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Rebuild state store from experiments",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--workspace",
        default="./autolab_workspace",
        help="Path to workspace directory",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Backup existing state before rebuilding",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be rebuilt without making changes",
    )

    args = parser.parse_args()

    # Load data
    workspace_path = Path(args.workspace).expanduser().resolve()
    experiment_store = ExperimentStore(str(workspace_path))
    result_store = ResultStore(str(workspace_path))
    state_store = StateStore(str(workspace_path))

    # Load existing state
    old_state = state_store.load()

    if old_state and args.backup:
        backup_path = workspace_path / "state" / f"backup_{_now_filesafe()}.json"
        import shutil
        shutil.copy(state_store._state_file, backup_path)
        print(f"Backed up existing state to {backup_path}")

    # Analyze experiments
    experiments = experiment_store.load_all()
    results = result_store.load_all()

    print(f"Analyzing {len(experiments)} experiment(s)...")

    # Build new state
    new_state = state_store._create_default()

    # Count by status
    status_counts = defaultdict(int)
    for exp in experiments.values():
        status_counts[exp.status] += 1

    # Get best results by family
    best_results = {}
    for exp_id, exp in experiments.items():
        if exp.status == "completed" and exp.family:
            result = results.get(exp_id)
            if result and result.metrics:
                if exp.family not in best_results:
                    best_results[exp.family] = (exp_id, result)
                else:
                    # Compare based on first metric
                    best_id, best_res = best_results[exp.family]
                    first_metric = next(iter(result.metrics.keys()), None)
                    if first_metric and first_metric in best_res.metrics:
                        if result.metrics[first_metric] > best_res.metrics[first_metric]:
                            best_results[exp.family] = (exp_id, result)

    # Count failures by type
    failure_counts = defaultdict(int)
    for exp_id, exp in experiments.items():
        if exp.status == "failed":
            result = results.get(exp_id)
            if result and result.failure_type:
                failure_counts[result.failure_type] += 1

    # Populate new state
    new_state.experiment_count = len(experiments)
    new_state.cycle_count = max(1, sum(1 for exp in experiments.values() if exp.cycle) // 10 + 1)

    # Use best results as baselines if no baselines set
    if not new_state.baselines and best_results:
        for family, (exp_id, _) in best_results.items():
            new_state.baselines[family] = exp_id

    new_state.last_updated_at = _now()
    new_state.last_action = "rebuild_state"

    # Print summary
    print("\nCurrent state:")
    print(f"  Total experiments: {len(experiments)}")
    print(f"  By status:")
    for status in ExperimentStatus:
        print(f"    {status}: {status_counts.get(status, 0)}")

    print(f"\nBest results by family:")
    for family, (exp_id, result) in sorted(best_results.items()):
        exp = experiments[exp_id]
        print(f"  {family}: {exp_id[:12]} - {result}")

    print(f"\nFailures by type:")
    for ftype, count in sorted(failure_counts.items(), key=lambda x: -x[1]):
        print(f"  {ftype}: {count}")

    print(f"\nBaselines:")
    if new_state.baselines:
        for family, exp_id in sorted(new_state.baselines.items()):
            exp = experiments.get(exp_id)
            title = exp.title[:40] + "..." if exp and len(exp.title) > 40 else exp.title if exp else "N/A"
            print(f"  {family}: {exp_id[:12]} ({title})")
    else:
        print("  None")

    if old_state:
        print(f"\nOld state:")
        print(f"  Experiment count: {old_state.experiment_count}")
        print(f"  Cycle count: {old_state.cycle_count}")
        print(f"  Last action: {old_state.last_action}")

    # Save or show dry run
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - state not updated")
    else:
        state_store.save(new_state)
        print("\nState rebuilt successfully")

    return 0


def _now():
    """Get current timestamp.

    Returns:
        ISO format timestamp.
    """
    return datetime.utcnow().isoformat() + "Z"


def _now_filesafe():
    """Get current timestamp for filename.

    Returns:
        Filesafe timestamp string.
    """
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


if __name__ == "__main__":
    sys.exit(main())
