"""OpenClaw skill: autolab_get_history

Get experiment history.
"""

from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.result_store import ResultStore


def execute(args: dict) -> dict:
    """Execute the get_history skill.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with experiment history.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    limit = args.get("limit", 20)
    status = args.get("status")  # Optional: filter by status

    # Load data
    experiment_store = ExperimentStore(workspace_path)
    result_store = ResultStore(workspace_path)

    experiments = experiment_store.load_all()
    results = result_store.load_all()

    # Filter by status if specified
    if status:
        experiments = {k: v for k, v in experiments.items() if v.status == status}

    # Sort by creation time and limit
    sorted_experiments = sorted(
        experiments.values(),
        key=lambda e: e.created_at,
        reverse=True,
    )[:limit]

    # Build response
    history = []
    for exp in sorted_experiments:
        entry = {
            "experiment_id": exp.id,
            "title": exp.title,
            "description": exp.description,
            "status": exp.status,
            "family": exp.family,
            "created_at": exp.created_at,
            "priority": exp.priority,
        }

        # Add result if available
        if exp.id in results:
            result = results[exp.id]
            entry["success"] = result.success
            entry["metrics"] = result.metrics
            entry["runtime_seconds"] = result.runtime_seconds

        history.append(entry)

    return {
        "success": True,
        "history": history,
        "total": len(history),
    }


def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Skill specification dictionary.
    """
    return {
        "name": "autolab_get_history",
        "description": "Get experiment history, optionally filtered by status",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "Path to autolab workspace",
                    "default": "./autolab_workspace",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of experiments to return",
                    "default": 20,
                },
                "status": {
                    "type": "string",
                    "description": "Filter by experiment status",
                    "enum": ["pending", "ready", "running", "completed", "failed", "blocked", "canceled"],
                },
            },
            "required": [],
        },
    }
