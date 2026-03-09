"""OpenClaw skill: autolab_stop_branch

Stop/cancel a branch of experiments.
"""

from autolab.storage.experiment_store import ExperimentStore


def _get_descendants(
    experiment_store: ExperimentStore,
    root_id: str,
    visited: set | None = None,
) -> set[str]:
    """Get all descendants of an experiment.

    Args:
        experiment_store: Experiment store.
        root_id: Root experiment ID.
        visited: Set of already visited IDs.

    Returns:
        Set of descendant experiment IDs.
    """
    if visited is None:
        visited = set()

    if root_id in visited:
        return set()

    visited.add(root_id)

    all_experiments = experiment_store.load_all()
    descendants = {root_id}

    for exp in all_experiments.values():
        if exp.parent_experiment_id == root_id:
            descendants.update(
                _get_descendants(experiment_store, exp.id, visited)
            )

    return descendants


def execute(args: dict) -> dict:
    """Execute stop_branch skill.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with stop result.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    experiment_id = args.get("experiment_id")
    reason = args.get("reason", "")
    cancel_running = args.get("cancel_running", False)

    # Validate required fields
    if not experiment_id:
        return {
            "success": False,
            "error": "Missing required field: experiment_id",
        }

    # Load experiments
    experiment_store = ExperimentStore(workspace_path)
    all_experiments = experiment_store.load_all()

    # Check root experiment exists
    if experiment_id not in all_experiments:
        return {
            "success": False,
            "error": f"Experiment not found: {experiment_id}",
        }

    # Get all descendants
    descendant_ids = _get_descendants(experiment_store, experiment_id)

    # Filter experiments that can be stopped
    to_stop = []
    errors = []

    for exp_id in descendant_ids:
        exp = all_experiments[exp_id]

        # Check status
        if exp.status in ["completed", "failed", "canceled"]:
            continue  # Already finished

        if exp.status == "running" and not cancel_running:
            errors.append(f"Cannot stop running experiment {exp_id} without cancel_running=True")
            continue

        # Mark for stopping
        to_stop.append(exp_id)

    # Update experiments
    for exp_id in to_stop:
        try:
            experiment_store.update(
                exp_id,
                status="canceled",
            )
        except Exception as e:
            errors.append(f"Failed to stop {exp_id}: {e}")

    return {
        "success": len(errors) == 0,
        "stopped": {
            "root_experiment_id": experiment_id,
            "stopped_count": len(to_stop),
            "stopped_experiments": to_stop,
            "cancel_running": cancel_running,
            "reason": reason,
            "error_count": len(errors),
            "errors": errors,
        },
    }


def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Skill specification dictionary.
    """
    return {
        "name": "autolab_stop_branch",
        "description": "Stop/cancel a branch of experiments (root and all descendants)",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "Path to autolab workspace",
                    "default": "./autolab_workspace",
                },
                "experiment_id": {
                    "type": "string",
                    "description": "Root experiment ID of branch to stop",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for stopping the branch",
                },
                "cancel_running": {
                    "type": "boolean",
                    "description": "Whether to cancel currently running experiments in branch",
                    "default": False,
                },
            },
            "required": ["experiment_id"],
        },
    }
