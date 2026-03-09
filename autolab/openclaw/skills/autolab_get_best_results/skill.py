"""OpenClaw skill: autolab_get_best_results

Get best results per family/metric.
"""

from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.result_store import ResultStore


def execute(args: dict) -> dict:
    """Execute get_best_results skill.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with best results.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    family = args.get("family")  # Optional: filter by family
    metric_name = args.get("metric_name")  # Optional: filter by metric
    higher_is_better = args.get("higher_is_better", True)  # Default: higher is better

    # Load data
    result_store = ResultStore(workspace_path)
    experiment_store = ExperimentStore(workspace_path)

    results = result_store.load_all()
    experiments = experiment_store.load_all()

    # Filter by family if specified
    if family:
        family_exps = experiment_store.get_by_family(family)
        results = {k: v for k, v in results.items() if k in family_exps}

    # Get best result
    metric = metric_name or "val_acc"  # Default metric
    best_result = result_store.get_best_for_metric(metric, higher_is_better)

    if not best_result:
        return {
            "success": True,
            "best_results": {},
            "metric": metric,
        }

    # Get experiment info
    experiment = experiments.get(best_result.experiment_id)

    # Build response
    best_info = {
        "experiment_id": best_result.experiment_id,
        "metric_name": metric,
        "metric_value": best_result.metrics.get(metric),
        "success": best_result.success,
        "runtime_seconds": best_result.runtime_seconds,
    }

    if experiment:
        best_info["title"] = experiment.title
        best_info["family"] = experiment.family
        best_info["created_at"] = experiment.created_at

    return {
        "success": True,
        "best_results": {family or "all": best_info},
        "metric": metric,
    }


def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Skill specification dictionary.
    """
    return {
        "name": "autolab_get_best_results",
        "description": "Get best experiment results per family or overall",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "Path to autolab workspace",
                    "default": "./autolab_workspace",
                },
                "family": {
                    "type": "string",
                    "description": "Filter by family name",
                },
                "metric_name": {
                    "type": "string",
                    "description": "Metric to optimize (e.g., 'val_acc', 'test_acc')",
                },
                "higher_is_better": {
                    "type": "boolean",
                    "description": "Whether higher metric values are better",
                    "default": True,
                },
            },
            "required": [],
        },
    }
