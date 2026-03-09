"""Action validator for validating planner actions."""

import json
from pathlib import Path
from typing import Any

from autolab.schemas.action import PlannerAction
from autolab.schemas.experiment import Experiment


class ValidationError(Exception):
    """Error raised when validation fails."""

    pass


class ActionValidator:
    """Validator for planner actions."""

    def __init__(
        self,
        workspace_path: str = "./autolab_workspace",
        allow_code_patching: bool = False,
    ) -> None:
        """Initialize action validator.

        Args:
            workspace_path: Path to workspace.
            allow_code_patching: Whether code patching is allowed.
        """
        self.workspace_path = Path(workspace_path).expanduser().resolve()
        self.allow_code_patching = allow_code_patching

    def validate_all(
        self,
        actions: list[PlannerAction],
        policy_constraints: dict[str, Any],
        experiments: dict[str, Experiment],
    ) -> tuple[list[PlannerAction], list[tuple[int, str]]]:
        """Validate all actions.

        Args:
            actions: List of planner actions.
            policy_constraints: Policy constraints.
            experiments: All experiments.

        Returns:
            Tuple of (valid_actions, errors) where errors is list of (index, error).
        """
        valid_actions = []
        errors = []

        for i, action in enumerate(actions):
            try:
                self._validate_single_action(action, policy_constraints, experiments)
                valid_actions.append(action)
            except ValidationError as e:
                errors.append((i, str(e)))

        return valid_actions, errors

    def _validate_single_action(
        self,
        action: PlannerAction,
        policy_constraints: dict[str, Any],
        experiments: dict[str, Experiment],
    ) -> None:
        """Validate a single action.

        Args:
            action: Planner action.
            policy_constraints: Policy constraints.
            experiments: All experiments.

        Raises:
            ValidationError: If validation fails.
        """
        # Validate action type
        self._validate_action_type(action)

        # Validate against policies
        self._validate_policies(action, policy_constraints)

        # Validate payload based on action type
        self._validate_payload(action, experiments)

        # Validate dependencies
        self._validate_dependencies(action, experiments)

    def _validate_action_type(self, action: PlannerAction) -> None:
        """Validate action type.

        Args:
            action: Planner action.

        Raises:
            ValidationError: If action type is invalid.
        """
        valid_types = [
            "create_experiment",
            "create_hypothesis",
            "patch_config",
            "patch_code",
            "rerank_queue",
            "archive_branch",
            "stop_branch",
            "request_report",
            "retry_experiment",
        ]

        if action.action_type not in valid_types:
            raise ValidationError(f"Invalid action type: {action.action_type}")

        if not action.rationale:
            raise ValidationError("Rationale is required")

        if not isinstance(action.payload, dict):
            raise ValidationError("Payload must be a dictionary")

    def _validate_policies(
        self,
        action: PlannerAction,
        policy_constraints: dict[str, Any],
    ) -> None:
        """Validate against policy constraints.

        Args:
            action: Planner action.
            policy_constraints: Policy constraints.

        Raises:
            ValidationError: If action violates policies.
        """
        planner_policies = policy_constraints.get("planner", {})
        patching_policies = policy_constraints.get("patching", {})
        safety_policies = policy_constraints.get("safety", {})

        # Check code patching permission
        if action.action_type == "patch_code":
            if not planner_policies.get("allow_code_patching", False):
                raise ValidationError("Code patching is not allowed by policy")

            # Check file allowlist
            target_file = action.payload.get("target_file")
            if target_file:
                allowed_files = patching_policies.get("allowed_code_files", [])
                if allowed_files and target_file not in allowed_files:
                    raise ValidationError(
                        f"File {target_file} not in allowed code files list"
                    )

        # Check protected paths
        protected_paths = safety_policies.get("protected_paths", [])
        for path in protected_paths:
            if path in str(action.payload.get("target_file", "")):
                raise ValidationError(f"Cannot patch protected path: {path}")

    def _validate_payload(
        self,
        action: PlannerAction,
        experiments: dict[str, Experiment],
    ) -> None:
        """Validate action payload.

        Args:
            action: Planner action.
            experiments: All experiments.

        Raises:
            ValidationError: If payload is invalid.
        """
        payload = action.payload

        if action.action_type == "create_experiment":
            self._validate_create_experiment(payload, experiments)

        elif action.action_type == "create_hypothesis":
            self._validate_create_hypothesis(payload)

        elif action.action_type == "patch_config":
            self._validate_patch_config(payload, experiments)

        elif action.action_type == "patch_code":
            self._validate_patch_code(payload)

        elif action.action_type == "rerank_queue":
            self._validate_rerank_queue(payload, experiments)

        elif action.action_type == "stop_branch":
            self._validate_stop_branch(payload, experiments)

        elif action.action_type == "request_report":
            self._validate_request_report(payload)

        elif action.action_type == "retry_experiment":
            self._validate_retry_experiment(payload, experiments)

        elif action.action_type == "archive_branch":
            self._validate_archive_branch(payload, experiments)

    def _validate_create_experiment(
        self,
        payload: dict[str, Any],
        experiments: dict[str, Experiment],
    ) -> None:
        """Validate create_experiment payload.

        Args:
            payload: Action payload.
            experiments: All experiments.

        Raises:
            ValidationError: If payload is invalid.
        """
        required_fields = ["title", "description", "objective"]
        for field in required_fields:
            if field not in payload:
                raise ValidationError(f"Missing required field: {field}")

        # Check for duplicate experiment
        if "title" in payload:
            title = payload["title"]
            for exp in experiments.values():
                if exp.title == title and exp.status not in ["completed", "failed", "canceled"]:
                    raise ValidationError(
                        f"Experiment with title '{title}' already active"
                    )

    def _validate_create_hypothesis(self, payload: dict[str, Any]) -> None:
        """Validate create_hypothesis payload.

        Args:
            payload: Action payload.

        Raises:
            ValidationError: If payload is invalid.
        """
        required_fields = ["title", "rationale", "expected_effect"]
        for field in required_fields:
            if field not in payload:
                raise ValidationError(f"Missing required field: {field}")

    def _validate_patch_config(
        self,
        payload: dict[str, Any],
        experiments: dict[str, Experiment],
    ) -> None:
        """Validate patch_config payload.

        Args:
            payload: Action payload.
            experiments: All experiments.

        Raises:
            ValidationError: If payload is invalid.
        """
        if "experiment_id" not in payload:
            raise ValidationError("Missing required field: experiment_id")

        exp_id = payload["experiment_id"]
        if exp_id not in experiments:
            raise ValidationError(f"Experiment not found: {exp_id}")

        if "config_patch" not in payload:
            raise ValidationError("Missing required field: config_patch")

        if not isinstance(payload["config_patch"], dict):
            raise ValidationError("config_patch must be a dictionary")

    def _validate_patch_code(self, payload: dict[str, Any]) -> None:
        """Validate patch_code payload.

        Args:
            payload: Action payload.

        Raises:
            ValidationError: If payload is invalid.
        """
        if "target_file" not in payload:
            raise ValidationError("Missing required field: target_file")

        if "patch_content" not in payload:
            raise ValidationError("Missing required field: patch_content")

        # Check if file exists
        target_path = Path(payload["target_file"]).expanduser().resolve()
        if not target_path.exists():
            raise ValidationError(f"Target file not found: {target_path}")

        # Check if file is in git repo
        repo_root = Path(".").resolve()
        try:
            # Check if file is under repo
            target_path.relative_to(repo_root)
        except ValueError:
            raise ValidationError("Target file must be in repository")

    def _validate_rerank_queue(
        self,
        payload: dict[str, Any],
        experiments: dict[str, Experiment],
    ) -> None:
        """Validate rerank_queue payload.

        Args:
            payload: Action payload.
            experiments: All experiments.

        Raises:
            ValidationError: If payload is invalid.
        """
        if "experiment_priorities" not in payload:
            raise ValidationError("Missing required field: experiment_priorities")

        priorities = payload["experiment_priorities"]
        if not isinstance(priorities, dict):
            raise ValidationError("experiment_priorities must be a dictionary")

        # Check that all referenced experiments exist
        for exp_id in priorities.keys():
            if exp_id not in experiments:
                raise ValidationError(f"Experiment not found: {exp_id}")

            # Check priority value
            priority = priorities[exp_id]
            if not isinstance(priority, (int, float)):
                raise ValidationError(f"Priority must be numeric: {priority}")

    def _validate_stop_branch(
        self,
        payload: dict[str, Any],
        experiments: dict[str, Experiment],
    ) -> None:
        """Validate stop_branch payload.

        Args:
            payload: Action payload.
            experiments: All experiments.

        Raises:
            ValidationError: If payload is invalid.
        """
        if "experiment_id" not in payload:
            raise ValidationError("Missing required field: experiment_id")

        exp_id = payload["experiment_id"]
        if exp_id not in experiments:
            raise ValidationError(f"Experiment not found: {exp_id}")

    def _validate_request_report(self, payload: dict[str, Any]) -> None:
        """Validate request_report payload.

        Args:
            payload: Action payload.

        Raises:
            ValidationError: If payload is invalid.
        """
        if "report_type" not in payload:
            raise ValidationError("Missing required field: report_type")

        valid_types = ["cycle", "experiment", "family", "summary"]
        if payload["report_type"] not in valid_types:
            raise ValidationError(f"Invalid report_type: {payload['report_type']}")

    def _validate_retry_experiment(
        self,
        payload: dict[str, Any],
        experiments: dict[str, Experiment],
    ) -> None:
        """Validate retry_experiment payload.

        Args:
            payload: Action payload.
            experiments: All experiments.

        Raises:
            ValidationError: If payload is invalid.
        """
        if "experiment_id" not in payload:
            raise ValidationError("Missing required field: experiment_id")

        exp_id = payload["experiment_id"]
        if exp_id not in experiments:
            raise ValidationError(f"Experiment not found: {exp_id}")

        exp = experiments[exp_id]
        if exp.status not in ["failed"]:
            raise ValidationError(f"Can only retry failed experiments, status: {exp.status}")

    def _validate_archive_branch(
        self,
        payload: dict[str, Any],
        experiments: dict[str, Experiment],
    ) -> None:
        """Validate archive_branch payload.

        Args:
            payload: Action payload.
            experiments: All experiments.

        Raises:
            ValidationError: If payload is invalid.
        """
        if "experiment_id" not in payload:
            raise ValidationError("Missing required field: experiment_id")

        exp_id = payload["experiment_id"]
        if exp_id not in experiments:
            raise ValidationError(f"Experiment not found: {exp_id}")

    def _validate_dependencies(
        self,
        action: PlannerAction,
        experiments: dict[str, Experiment],
    ) -> None:
        """Validate that dependencies exist and are valid.

        Args:
            action: Planner action.
            experiments: All experiments.

        Raises:
            ValidationError: If dependencies are invalid.
        """
        payload = action.payload

        # Check parent_experiment_id
        if "parent_experiment_id" in payload:
            parent_id = payload["parent_experiment_id"]
            if parent_id not in experiments:
                raise ValidationError(f"Parent experiment not found: {parent_id}")

        # Check baseline_experiment_id
        if "baseline_experiment_id" in payload:
            baseline_id = payload["baseline_experiment_id"]
            if baseline_id not in experiments:
                raise ValidationError(f"Baseline experiment not found: {baseline_id}")
