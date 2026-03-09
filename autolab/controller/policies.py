"""Policy management for the controller."""

import json
from pathlib import Path
from typing import Any


class PolicyManager:
    """Manager for system policies."""

    def __init__(
        self,
        config_path: str = "./autolab/configs/policies.yaml",
    ) -> None:
        """Initialize policy manager.

        Args:
            config_path: Path to policies configuration file.
        """
        self.config_path = Path(config_path).expanduser().resolve()
        self.policies = self._load_policies()

    def _load_policies(self) -> dict[str, Any]:
        """Load policies from config file.

        Returns:
            Dictionary of policies.
        """
        if not self.config_path.exists():
            return self._get_default_policies()

        with open(self.config_path) as f:
            if self.config_path.suffix == ".json":
                return json.load(f)
            else:
                return self._load_yaml(f)

    def _load_yaml(self, file_obj: Any) -> dict:
        """Load YAML file.

        Args:
            file_obj: File object.

        Returns:
            Dictionary with YAML content.
        """
        import yaml

        return yaml.safe_load(file_obj)

    def _get_default_policies(self) -> dict[str, Any]:
        """Get default policies.

        Returns:
            Default policies dictionary.
        """
        return {
            "planner": {
                "allow_code_patching": False,
                "max_new_experiments_per_cycle": 3,
                "max_hypotheses_per_cycle": 2,
            },
            "executor": {
                "max_concurrent_jobs": 2,
                "retry_transient_failures": True,
                "stall_timeout_minutes": 30,
            },
            "patching": {
                "allowed_config_paths": [
                    "train.lr",
                    "train.batch_size",
                    "train.weight_decay",
                    "model.dropout",
                    "model.sparsity_lambda",
                    "data.augmentation",
                ],
                "allowed_code_files": [
                    "models/attention.py",
                    "losses/custom_loss.py",
                ],
            },
            "safety": {
                "protected_paths": [
                    ".git",
                    "secrets/",
                    "ssh_keys/",
                ],
                "duplicate_experiment_check": True,
            },
        }

    def get_planner_policies(self) -> dict[str, Any]:
        """Get planner-related policies.

        Returns:
            Planner policies.
        """
        return self.policies.get("planner", {})

    def get_executor_policies(self) -> dict[str, Any]:
        """Get executor-related policies.

        Returns:
            Executor policies.
        """
        return self.policies.get("executor", {})

    def get_patching_policies(self) -> dict[str, Any]:
        """Get patching-related policies.

        Returns:
            Patching policies.
        """
        return self.policies.get("patching", {})

    def get_safety_policies(self) -> dict[str, Any]:
        """Get safety-related policies.

        Returns:
            Safety policies.
        """
        return self.policies.get("safety", {})

    def get_all(self) -> dict[str, Any]:
        """Get all policies.

        Returns:
            All policies.
        """
        return self.policies.copy()

    def update_policy(
        self,
        category: str,
        key: str,
        value: Any,
    ) -> None:
        """Update a policy value.

        Args:
            category: Policy category.
            key: Policy key.
            value: New value.
        """
        if category not in self.policies:
            self.policies[category] = {}

        self.policies[category][key] = value

    def allow_code_patching(self) -> bool:
        """Check if code patching is allowed.

        Returns:
            True if allowed.
        """
        return self.policies.get("planner", {}).get("allow_code_patching", False)

    def max_experiments_per_cycle(self) -> int:
        """Get max experiments per cycle.

        Returns:
            Max experiments.
        """
        return self.policies.get("planner", {}).get("max_new_experiments_per_cycle", 3)

    def max_hypotheses_per_cycle(self) -> int:
        """Get max hypotheses per cycle.

        Returns:
            Max hypotheses.
        """
        return self.policies.get("planner", {}).get("max_hypotheses_per_cycle", 2)

    def is_config_path_allowed(self, path: str) -> bool:
        """Check if a config path can be patched.

        Args:
            path: Config path.

        Returns:
            True if allowed.
        """
        allowed_paths = self.policies.get("patching", {}).get("allowed_config_paths", [])

        if not allowed_paths:
            return True

        # Check if path matches or is under allowed path
        for allowed in allowed_paths:
            if path == allowed or path.startswith(allowed + "."):
                return True

        return False

    def is_code_file_allowed(self, file_path: str) -> bool:
        """Check if a code file can be patched.

        Args:
            file_path: Code file path.

        Returns:
            True if allowed.
        """
        allowed_files = self.policies.get("patching", {}).get("allowed_code_files", [])

        if not allowed_files:
            return False

        file_path = Path(file_path).name
        return file_path in allowed_files

    def is_protected_path(self, path: str) -> bool:
        """Check if a path is protected.

        Args:
            path: Path to check.

        Returns:
            True if protected.
        """
        protected = self.policies.get("safety", {}).get("protected_paths", [])

        for prot_path in protected:
            if path.startswith(prot_path):
                return True

        return False

    def save(self, output_path: str | None = None) -> None:
        """Save policies to file.

        Args:
            output_path: Optional output path.
        """
        save_path = Path(output_path) if output_path else self.config_path

        with open(save_path, "w") as f:
            if save_path.suffix == ".json":
                json.dump(self.policies, f, indent=2)
            else:
                import yaml

                yaml.dump(self.policies, f, default_flow_style=False)
