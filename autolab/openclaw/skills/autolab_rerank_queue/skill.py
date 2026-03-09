"""OpenClaw skill: autolab_rerank_queue

Reorder experiment priorities.
"""

from autolab.storage.experiment_store import ExperimentStore


def execute(args: dict) -> dict:
    """Execute rerank_queue skill.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with rerank result.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    experiment_priorities = args.get("experiment_priorities", {})
    rationale = args.get("rationale", "")

    # Validate input
    if not experiment_priorities:
        return {
            "success": False,
            "error": "No priorities provided",
        }

    if not isinstance(experiment_priorities, dict):
        return {
            "success": False,
            "error": "experiment_priorities must be a dictionary",
        }

    # Load experiments
    experiment_store = ExperimentStore(workspace_path)
    all_experiments = experiment_store.load_all()

    updated = []
    errors = []

    for exp_id, new_priority in experiment_priorities.items():
        # Validate experiment exists
        if exp_id not in all_experiments:
            errors.append(f"Experiment not found: {exp_id}")
            continue

        # Validate priority value
        if not isinstance(new_priority, (int, float)):
            errors.append(f"Invalid priority for {exp_id}: must be numeric")
            continue

        # Validate priority range
        if new_priority < 0 or new_priority > 100:
            errors.append(f"Invalid priority for {exp_id}: must be between 0 and 100")
            continue

        # Update experiment
        try:
            experiment_store.update(exp_id, priority=float(new_priority))
            updated.append({
                "experiment_id": exp_id,
                "old_priority": all_experiments[exp_id].priority,
                "new_priority": float(new_priority),
            })
        except Exception as e:
            errors.append(f"Failed to update {exp_id}: {e}")

    return {
        "success": len(errors) == 0,
        "reranked": {
            "updated_count": len(updated),
            "updated": updated,
            "error_count": len(errors),
            "errors": errors,
            "rationale": rationale,
        },
    }


def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Skill specification dictionary.
    """
    return {
        "name": "autolab_rerank_queue",
        "description": "Reorder experiment priorities in the queue",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "Path to autolab workspace",
                    "default": "./autolab_workspace",
                },
                "experiment_priorities": {
                    "type": "object",
                    "description": "Dictionary mapping experiment IDs to new priorities (0-100)",
                },
                "rationale": {
                    "type": "string",
                    "description": "Reason for reordering",
                },
            },
            "required": ["experiment_priorities"],
        },
    }
