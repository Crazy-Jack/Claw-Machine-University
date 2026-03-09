"""OpenClaw skill: autolab_get_failures

Get failure information.
"""

from autolab.storage.result_store import ResultStore


def execute(args: dict) -> dict:
    """Execute the get_failures skill.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with failure information.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    limit = args.get("limit", 10)
    failure_type = args.get("failure_type")  # Optional: filter by type

    # Load results
    result_store = ResultStore(workspace_path)
    all_results = result_store.load_all()

    # Get failed results
    failed_results = [
        (exp_id, result)
        for exp_id, result in all_results.items()
        if not result.success
    ]

    # Filter by failure type if specified
    if failure_type:
        failed_results = [
            (exp_id, result)
            for exp_id, result in failed_results
            if result.failure_type == failure_type
        ]

    # Sort by parsed time and limit
    failed_results.sort(key=lambda x: x[1].parsed_at, reverse=True)
    failed_results = failed_results[:limit]

    # Build response
    failures = []
    for exp_id, result in failed_results:
        entry = {
            "experiment_id": exp_id,
            "failure_type": result.failure_type,
            "failure_reason": result.failure_reason,
            "exit_code": result.exit_code,
            "parsed_at": result.parsed_at,
            "runtime_seconds": result.runtime_seconds,
        }
        failures.append(entry)

    # Get failure summary
    from autolab.storage.state_store import StateStore
    state_store = StateStore(workspace_path)
    results_dict = {exp_id: r for exp_id, r in all_results.items()}
    failure_summary = state_store.get_failure_summary(results_dict)

    return {
        "success": True,
        "failures": failures,
        "summary": {
            "total_failures": failure_summary.total_failures,
            "recent_failure_types": failure_summary.recent_failure_types,
        },
    }


def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Skill specification dictionary.
    """
    return {
        "name": "autolab_get_failures",
        "description": "Get information about failed experiments",
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
                    "description": "Maximum number of failures to return",
                    "default": 10,
                },
                "failure_type": {
                    "type": "string",
                    "description": "Filter by failure type (e.g., 'oom', 'timeout')",
                },
            },
            "required": [],
        },
    }
