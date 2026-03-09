"""OpenClaw skill: autolab_patch_config

Patch an experiment's configuration.
"""

from autolab.storage.experiment_store import ExperimentStore


def execute(args: dict) -> dict:
    """Execute patch_config skill.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with patch result.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    experiment_id = args.get("experiment_id")
    config_patch = args.get("config_patch")
    rationale = args.get("rationale", "")

    # Validate required fields
    if not experiment_id:
        return {
            "success": False,
            "error": "Missing required field: experiment_id",
        }

    if not config_patch:
        return {
            "success": False,
            "error": "Missing required field: config_patch",
        }

    if not isinstance(config_patch, dict):
        return {
            "success": False,
            "error": "config_patch must be a dictionary",
        }

    # Load experiment
    experiment_store = ExperimentStore(workspace_path)
    experiment = experiment_store.load(experiment_id)

    if not experiment:
        return {
            "success": False,
            "error": f"Experiment not found: {experiment_id}",
        }

    # Check experiment status
    if experiment.status not in ["pending", "ready"]:
        return {
            "success": False,
            "error": f"Cannot patch experiment with status: {experiment.status}",
        }

    # Get current config snapshot
    current_config = experiment.config_snapshot.copy()

    # Apply patches
    for key, value in config_patch.items():
        # Support dot notation (e.g., "train.lr")
        keys = key.split(".")
        config = current_config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    # Update experiment
    try:
        experiment_store.update(
            experiment_id,
            config_snapshot=current_config,
        )
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to update experiment: {e}",
        }

    return {
        "success": True,
        "patched": {
            "experiment_id": experiment_id,
            "config_changes": config_patch,
            "rationale": rationale,
        },
    }


def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Skill specification dictionary.
    """
    return {
        "name": "autolab_patch_config",
        "description": "Patch an experiment's configuration (safe, no code changes)",
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
                    "description": "Experiment ID to patch",
                },
                "config_patch": {
                    "type": "object",
                    "description": "Config changes (supports dot notation, e.g., {'train.lr': 0.001})",
                },
                "rationale": {
                    "type": "string",
                    "description": "Reason for the patch",
                },
            },
            "required": ["experiment_id", "config_patch"],
        },
    }
