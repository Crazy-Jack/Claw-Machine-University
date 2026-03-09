"""OpenClaw skill: autolab_compare_experiments

Compare experiment results against baselines or best in family.
"""

from autolab.evaluator.comparator import Comparator
from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.result_store import ResultStore


def execute(args: dict) -> dict:
    """Execute compare_experiments skill.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with comparison results.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    experiment_id = args.get("experiment_id")
    baseline_id = args.get("baseline_id")
    compare_to_best_in_family = args.get("compare_to_best_in_family", False)
    primary_metric = args.get("primary_metric", "val_acc")
    higher_is_better = args.get("higher_is_better", True)

    if not experiment_id:
        return {
            "success": False,
            "error": "experiment_id is required",
        }

    # Load data
    result_store = ResultStore(workspace_path)
    experiment_store = ExperimentStore(workspace_path)

    results = result_store.load_all()
    experiments = experiment_store.load_all()

    current = results.get(experiment_id)
    if not current:
        return {
            "success": False,
            "error": f"Experiment {experiment_id} has no results",
        }

    current_exp = experiments.get(experiment_id)
    if not current_exp:
        return {
            "success": False,
            "error": f"Experiment {experiment_id} not found",
        }

    # Initialize comparator
    comparator = Comparator(
        primary_metric=primary_metric,
        higher_is_better=higher_is_better,
    )

    # Perform comparison
    if baseline_id:
        # Compare to specific baseline
        baseline = results.get(baseline_id)
        if not baseline:
            return {
                "success": False,
                "error": f"Baseline {baseline_id} has no results",
            }

        baseline_exp = experiments.get(baseline_id)
        if not baseline_exp:
            return {
                "success": False,
                "error": f"Baseline {baseline_id} not found",
            }

        comparison = comparator.compare(current, baseline, current_exp, baseline_exp)
        comparison_dict = comparison.model_dump()
    elif compare_to_best_in_family and current_exp.family:
        # Compare to best in family
        comparison = comparator.compare_to_best_in_family(
            current,
            results,
            current_exp.family,
            primary_metric,
        )
        if not comparison:
            return {
                "success": False,
                "error": f"No other successful results in family {current_exp.family}",
            }
        comparison_dict = comparison.model_dump()
    else:
        return {
            "success": False,
            "error": "Either baseline_id or compare_to_best_in_family=True with family is required",
        }

    return {
        "success": True,
        "comparison": comparison_dict,
    }


def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Skill specification dictionary.
    """
    return {
        "name": "autolab_compare_experiments",
        "description": "Compare experiment results against baselines or best in family",
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
                    "description": "Current experiment ID to compare",
                },
                "baseline_id": {
                    "type": "string",
                    "description": "Baseline experiment ID to compare against",
                },
                "compare_to_best_in_family": {
                    "type": "boolean",
                    "description": "If true, compare to best result in the same family",
                    "default": False,
                },
                "primary_metric": {
                    "type": "string",
                    "description": "Primary metric for comparison",
                    "default": "val_acc",
                },
                "higher_is_better": {
                    "type": "boolean",
                    "description": "Whether higher metric values are better",
                    "default": True,
                },
            },
            "required": ["experiment_id"],
        },
    }
