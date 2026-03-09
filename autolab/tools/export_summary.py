"""Tool: export_summary

Export lab summary to JSON.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.result_store import ResultStore
from autolab.storage.state_store import StateStore


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Export lab summary to JSON",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--workspace",
        default="./autolab_workspace",
        help="Path to workspace directory",
    )
    parser.add_argument(
        "--output",
        default="lab_summary.json",
        help="Output JSON file path",
    )
    parser.add_argument(
        "--include-results",
        action="store_true",
        help="Include detailed results for each experiment",
    )

    args = parser.parse_args()

    # Load data
    workspace_path = Path(args.workspace).expanduser().resolve()
    experiment_store = ExperimentStore(str(workspace_path))
    result_store = ResultStore(str(workspace_path))
    state_store = StateStore(str(workspace_path))

    experiments = experiment_store.load_all()
    results = result_store.load_all()
    state = state_store.load()

    # Build summary
    summary = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "workspace": str(workspace_path),
        "experiments": {
            "total": len(experiments),
            "by_status": _count_by_status(experiments),
            "by_family": _count_by_family(experiments),
        },
        "state": state.dict() if state else None,
        "experiments_list": [],
    }

    # Add experiment details
    for exp_id, exp in sorted(
        experiments.items(),
        key=lambda x: x[1].created_at,
        reverse=True,
    ):
        exp_data = {
            "id": exp.id,
            "title": exp.title,
            "status": exp.status,
            "family": exp.family,
            "objective": exp.objective,
            "priority": exp.priority,
            "created_at": exp.created_at,
        }

        if args.include_results:
            exp_data.update({
                "description": exp.description,
                "worker_name": exp.worker_name,
                "gpu_id": exp.gpu_id,
                "started_at": exp.started_at,
                "finished_at": exp.finished_at,
                "tags": exp.tags,
                "dependencies": exp.dependencies,
                "result": results.get(exp_id).dict() if results.get(exp_id) else None,
            })

        summary["experiments_list"].append(exp_data)

    # Export to file
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Summary exported to {output_path}")
    print(f"Total experiments: {summary['experiments']['total']}")

    return 0


def _count_by_status(experiments):
    """Count experiments by status.

    Args:
        experiments: Dict of experiment_id -> experiment.

    Returns:
        Dict of status -> count.
    """
    counts = {}
    for exp in experiments.values():
        counts[exp.status] = counts.get(exp.status, 0) + 1
    return counts


def _count_by_family(experiments):
    """Count experiments by family.

    Args:
        experiments: Dict of experiment_id -> experiment.

    Returns:
        Dict of family -> count.
    """
    counts = {}
    for exp in experiments.values():
        if exp.family:
            counts[exp.family] = counts.get(exp.family, 0) + 1
    return counts


if __name__ == "__main__":
    sys.exit(main())
