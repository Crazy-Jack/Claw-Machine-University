"""OpenClaw skill: autolab_dispatch_ready

Dispatch ready experiments to available workers.
"""

from autolab.executor.job_runner import JobRunner
from autolab.executor.worker_registry import WorkerRegistry
from autolab.storage.experiment_store import ExperimentStore


def execute(args: dict) -> dict:
    """Execute dispatch_ready skill.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with dispatch results.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    max_experiments = args.get("max_experiments", 10)

    # Load experiments
    experiment_store = ExperimentStore(workspace_path)
    experiments = experiment_store.load_all()

    # Get ready experiments
    ready_experiments = experiment_store.get_ready_experiments()

    if not ready_experiments:
        return {
            "success": True,
            "launched": 0,
            "results": [],
            "message": "No ready experiments to dispatch",
        }

    # Initialize worker registry and job runner
    worker_registry = WorkerRegistry(workspace_path)
    job_runner = JobRunner(worker_registry, workspace_path)

    # Sort by priority
    sorted_ready = sorted(
        ready_experiments.values(),
        key=lambda e: e.priority,
        reverse=True,
    )

    launched = []
    launched_count = 0

    for experiment in sorted_ready:
        if launched_count >= max_experiments:
            break

        # Check if we can schedule
        decision = job_runner._select_worker(experiment)
        if not decision:
            continue

        # Launch job
        result = job_runner.launch_experiment(experiment)

        if result.success:
            # Update experiment status
            experiment.status = "running"
            experiment.started_at = result.launch_time
            experiment.worker_name = result.worker_name
            experiment.gpu_id = result.gpu_id
            experiment.pid = result.pid

            # Save updated experiment
            experiment_store.save(experiment)

            launched.append({
                "experiment_id": experiment.id,
                "worker_name": result.worker_name,
                "gpu_id": result.gpu_id,
                "pid": result.pid,
            })
            launched_count += 1
        else:
            launched.append({
                "experiment_id": experiment.id,
                "success": False,
                "error": result.error_message,
            })

    return {
        "success": True,
        "launched": launched_count,
        "attempted": len(sorted_ready),
        "results": launched,
    }


def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Skill specification dictionary.
    """
    return {
        "name": "autolab_dispatch_ready",
        "description": "Dispatch ready experiments to available workers",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "Path to autolab workspace",
                    "default": "./autolab_workspace",
                },
                "max_experiments": {
                    "type": "integer",
                    "description": "Maximum number of experiments to dispatch",
                    "default": 10,
                },
            },
            "required": [],
        },
    }
