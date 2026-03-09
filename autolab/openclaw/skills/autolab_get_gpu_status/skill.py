"""OpenClaw skill: autolab_get_gpu_status

Get GPU worker status.
"""

from autolab.executor.worker_registry import WorkerRegistry


def execute(args: dict) -> dict:
    """Execute the get_gpu_status skill.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with GPU status.
    """
    config_path = args.get("config_path", "./autolab/configs/gpu.yaml")

    # Load worker registry
    worker_registry = WorkerRegistry(config_path)

    # Get summary
    summary = worker_registry.get_worker_summary()

    # Get detailed worker info
    workers = []
    for worker_name, worker in worker_registry.get_all().items():
        worker_info = {
            "name": worker_name,
            "status": worker.status,
            "enabled": worker.enabled,
            "host": worker.host,
            "current_jobs": worker.current_jobs,
            "max_concurrent_jobs": worker.max_concurrent_jobs,
            "gpus": [
                {
                    "id": gpu.id,
                    "type": gpu.type,
                    "memory_gb": gpu.memory_gb,
                }
                for gpu in worker.gpus
            ],
            "last_heartbeat": worker.last_heartbeat,
        }
        workers.append(worker_info)

    return {
        "success": True,
        "summary": summary,
        "workers": workers,
    }


def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Skill specification dictionary.
    """
    return {
        "name": "autolab_get_gpu_status",
        "description": "Get status of all GPU workers",
        "parameters": {
            "type": "object",
            "properties": {
                "config_path": {
                    "type": "string",
                    "description": "Path to GPU config file",
                    "default": "./autolab/configs/gpu.yaml",
                },
            },
            "required": [],
        },
    }
