"""Action router for routing planner actions to handlers."""

from typing import Any

from autolab.schemas.action import (
    PlannerAction,
    RerankQueuePayload,
    RequestReportPayload,
    StopBranchPayload,
)


class ActionRouter:
    """Router for handling planner actions."""

    def __init__(self) -> None:
        """Initialize action router."""
        pass

    def route(self, action: PlannerAction) -> str:
        """Route action to appropriate handler.

        Args:
            action: Planner action.

        Returns:
            Handler name.
        """
        action_handlers = {
            "create_experiment": "handle_create_experiment",
            "create_hypothesis": "handle_create_hypothesis",
            "patch_config": "handle_patch_config",
            "patch_code": "handle_patch_code",
            "rerank_queue": "handle_rerank_queue",
            "archive_branch": "handle_archive_branch",
            "stop_branch": "handle_stop_branch",
            "request_report": "handle_request_report",
            "retry_experiment": "handle_retry_experiment",
        }

        handler = action_handlers.get(action.action_type)
        if not handler:
            raise ValueError(f"Unknown action type: {action.action_type}")

        return handler

    def validate_action(
        self,
        action: PlannerAction,
        policy_constraints: dict[str, Any],
    ) -> tuple[bool, str]:
        """Validate an action against policy constraints.

        Args:
            action: Planner action.
            policy_constraints: Policy constraints.

        Returns:
            Tuple of (is_valid, reason).
        """
        planner_policies = policy_constraints.get("planner", {})

        # Check code patching permission
        if action.action_type == "patch_code":
            allow_code_patching = planner_policies.get("allow_code_patching", False)
            if not allow_code_patching:
                return False, "Code patching is not allowed by policy"

        # Check experiment limit
        if action.action_type == "create_experiment":
            max_per_cycle = planner_policies.get("max_new_experiments_per_cycle", 3)
            if max_per_cycle <= 0:
                return False, "No new experiments allowed this cycle"

        # Check hypothesis limit
        if action.action_type == "create_hypothesis":
            max_per_cycle = planner_policies.get("max_hypotheses_per_cycle", 2)
            if max_per_cycle <= 0:
                return False, "No new hypotheses allowed this cycle"

        # Validate payload structure
        try:
            self._validate_payload(action)
        except ValueError as e:
            return False, f"Invalid payload: {e}"

        return True, "Valid"

    def _validate_payload(self, action: PlannerAction) -> None:
        """Validate action payload structure.

        Args:
            action: Planner action.

        Raises:
            ValueError: If payload is invalid.
        """
        if action.action_type == "rerank_queue":
            RerankQueuePayload(**action.payload)
        elif action.action_type == "stop_branch":
            StopBranchPayload(**action.payload)
        elif action.action_type == "request_report":
            RequestReportPayload(**action.payload)

        # Other payloads would be validated in their respective handlers

    def get_required_resources(self, action: PlannerAction) -> dict[str, Any]:
        """Get resources required for an action.

        Args:
            action: Planner action.

        Returns:
            Dictionary of required resources.
        """
        resources = {"type": action.action_type}

        if action.action_type == "create_experiment":
            resources["requires_gpu"] = True
            resources["requires_storage"] = True

        elif action.action_type == "patch_code":
            resources["requires_validation"] = True
            resources["requires_git"] = True

        elif action.action_type == "patch_config":
            resources["requires_config_access"] = True

        return resources

    def estimate_execution_time(self, action: PlannerAction) -> float:
        """Estimate execution time for an action.

        Args:
            action: Planner action.

        Returns:
            Estimated time in seconds.
        """
        times = {
            "create_experiment": 1.0,
            "create_hypothesis": 1.0,
            "patch_config": 5.0,
            "patch_code": 30.0,
            "rerank_queue": 1.0,
            "archive_branch": 1.0,
            "stop_branch": 5.0,
            "request_report": 10.0,
            "retry_experiment": 1.0,
        }

        return times.get(action.action_type, 5.0)

    def is_blocking(self, action: PlannerAction) -> bool:
        """Check if action blocks subsequent actions.

        Args:
            action: Planner action.

        Returns:
            True if blocking.
        """
        blocking_actions = {"patch_code", "stop_branch"}
        return action.action_type in blocking_actions

    def get_action_dependencies(self, action: PlannerAction) -> list[str]:
        """Get dependencies for an action.

        Args:
            action: Planner action.

        Returns:
            List of dependency experiment IDs.
        """
        dependencies = []

        if action.action_type == "create_experiment":
            payload = action.payload
            if "parent_experiment_id" in payload:
                dependencies.append(payload["parent_experiment_id"])
            if "baseline_experiment_id" in payload:
                dependencies.append(payload["baseline_experiment_id"])

        elif action.action_type == "patch_config":
            if "experiment_id" in action.payload:
                dependencies.append(action.payload["experiment_id"])

        elif action.action_type == "patch_code":
            if "experiment_id" in action.payload:
                dependencies.append(action.payload["experiment_id"])

        elif action.action_type == "stop_branch":
            if "experiment_id" in action.payload:
                dependencies.append(action.payload["experiment_id"])

        return dependencies

    def summarize_action(self, action: PlannerAction) -> str:
        """Generate a human-readable summary of an action.

        Args:
            action: Planner action.

        Returns:
            Summary string.
        """
        if action.action_type == "create_experiment":
            title = action.payload.get("title", "unnamed")
            return f"Create experiment: {title}"

        elif action.action_type == "create_hypothesis":
            title = action.payload.get("title", "unnamed")
            return f"Create hypothesis: {title}"

        elif action.action_type == "patch_config":
            exp_id = action.payload.get("experiment_id", "unknown")
            return f"Patch config for {exp_id}"

        elif action.action_type == "patch_code":
            file = action.payload.get("target_file", "unknown")
            return f"Patch code in {file}"

        elif action.action_type == "rerank_queue":
            count = len(action.payload.get("experiment_priorities", {}))
            return f"Rerank queue ({count} experiments)"

        elif action.action_type == "stop_branch":
            exp_id = action.payload.get("experiment_id", "unknown")
            return f"Stop branch from {exp_id}"

        elif action.action_type == "request_report":
            report_type = action.payload.get("report_type", "unknown")
            return f"Generate {report_type} report"

        elif action.action_type == "retry_experiment":
            return "Retry experiment"

        else:
            return f"Action: {action.action_type}"
