"""OpenClaw skill: autolab_get_goal

Get the current research goal.
"""

import json
from pathlib import Path


def execute(args: dict) -> dict:
    """Execute the get_goal skill.

    Args:
        args: Arguments dictionary (empty for this skill).

    Returns:
        Dictionary with research goal.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")

    # Load state
    from autolab.storage.state_store import StateStore

    state_store = StateStore(workspace_path)
    global_state = state_store.load_global_state()

    goal = global_state.goal

    return {
        "success": True,
        "goal": {
            "title": goal.title,
            "description": goal.description,
            "objectives": goal.objectives,
            "constraints": goal.constraints,
            "baseline_experiment_id": goal.baseline_experiment_id,
            "target_metrics": goal.target_metrics,
            "created_at": goal.created_at,
        },
    }


def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Skill specification dictionary.
    """
    return {
        "name": "autolab_get_goal",
        "description": "Get the current research goal and objectives",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "Path to autolab workspace",
                    "default": "./autolab_workspace",
                },
            },
            "required": [],
        },
    }
