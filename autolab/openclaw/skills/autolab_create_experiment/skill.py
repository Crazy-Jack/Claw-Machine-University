"""OpenClaw skill: autolab_create_experiment

Create a new experiment.
"""

from datetime import datetime

from autolab.schemas.experiment import Experiment
from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.git_snapshot import GitSnapshot


def execute(args: dict) -> dict:
    """Execute create_experiment skill.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with created experiment.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    title = args.get("title")
    description = args.get("description")
    objective = args.get("objective")
    family = args.get("family")
    parent_experiment_id = args.get("parent_experiment_id")
    baseline_experiment_id = args.get("baseline_experiment_id")
    priority = args.get("priority", 1.0)
    tags = args.get("tags", [])
    config_patch = args.get("config_patch", {})
    config_path = args.get("config_path", "./config.yaml")
    resource_request = args.get("resource_request", {})
    launch_command = args.get("launch_command", [])
    working_dir = args.get("working_dir", ".")
    dataset_info = args.get("dataset_info", {})
    max_runtime_minutes = args.get("max_runtime_minutes")

    # Validate required fields
    if not title or not description or not objective:
        return {
            "success": False,
            "error": "Missing required fields: title, description, objective",
        }

    # Load experiment store
    experiment_store = ExperimentStore(workspace_path)

    # Check for duplicate
    all_experiments = experiment_store.load_all()
    for exp in all_experiments.values():
        if exp.title == title and exp.status not in ["completed", "failed", "canceled"]:
            return {
                "success": False,
                "error": f"Experiment with title '{title}' already active",
            }

    # Generate experiment ID
    exp_count = len(all_experiments) + 1
    exp_id = f"exp_{exp_count:04d}"

    # Get git snapshot
    git_snapshot = GitSnapshot(".").get_snapshot()

    # Create experiment
    experiment = Experiment(
        id=exp_id,
        hypothesis_id=None,
        title=title,
        description=description,
        objective=objective,
        family=family,
        parent_experiment_id=parent_experiment_id,
        baseline_experiment_id=baseline_experiment_id,
        status="pending",
        priority=priority,
        tags=tags,
        dependencies=[],
        config_path=config_path,
        config_snapshot=config_patch,
        code_snapshot=git_snapshot,
        resource_request=resource_request,
        launch_command=launch_command,
        working_dir=working_dir,
        dataset_info=dataset_info,
        planner_rationale=args.get("rationale", ""),
        created_by="openclaw",
        max_runtime_minutes=max_runtime_minutes,
        retry_count=0,
        max_retries=1,
        created_at=datetime.utcnow().isoformat() + "Z",
    )

    # Save
    try:
        experiment_store.add(experiment)
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
        }

    return {
        "success": True,
        "experiment": {
            "experiment_id": experiment.id,
            "title": experiment.title,
            "status": experiment.status,
            "family": experiment.family,
            "priority": experiment.priority,
            "created_at": experiment.created_at,
        },
    }


def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Skill specification dictionary.
    """
    return {
        "name": "autolab_create_experiment",
        "description": "Create a new experiment",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "Path to autolab workspace",
                    "default": "./autolab_workspace",
                },
                "title": {
                    "type": "string",
                    "description": "Experiment title",
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description",
                },
                "objective": {
                    "type": "string",
                    "description": "Research objective",
                },
                "family": {
                    "type": "string",
                    "description": "Experiment family/group",
                },
                "parent_experiment_id": {
                    "type": "string",
                    "description": "Parent experiment ID to branch from",
                },
                "baseline_experiment_id": {
                    "type": "string",
                    "description": "Baseline experiment for comparison",
                },
                "priority": {
                    "type": "number",
                    "description": "Priority (higher = more important)",
                    "default": 1.0,
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization",
                },
                "config_patch": {
                    "type": "object",
                    "description": "Config overrides (e.g., {'train.lr': 0.001})",
                },
                "config_path": {
                    "type": "string",
                    "description": "Path to config file",
                    "default": "./config.yaml",
                },
                "resource_request": {
                    "type": "object",
                    "description": "Resource requirements (gpu_memory_gb, batch_size, etc.)",
                },
                "launch_command": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command to launch experiment",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory",
                    "default": ".",
                },
                "dataset_info": {
                    "type": "object",
                    "description": "Dataset information",
                },
                "max_runtime_minutes": {
                    "type": "number",
                    "description": "Maximum allowed runtime in minutes",
                },
            },
            "required": ["title", "description", "objective"],
        },
    }
