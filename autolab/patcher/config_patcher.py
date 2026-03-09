"""Config patcher for applying configuration patches."""

from typing import Any


class ConfigPatcher:
    """Apply configuration patches to nested dictionaries."""

    def apply_patch(
        self,
        config: dict[str, Any],
        patch: dict[str, Any],
        strict: bool = False,
    ) -> dict[str, Any]:
        """Apply a patch to a configuration dictionary.

        Args:
            config: Original configuration dictionary.
            patch: Patch to apply. Can use dot notation for nested keys.
            strict: If True, raise error for invalid paths.

        Returns:
            Updated configuration.

        Raises:
            ValueError: If strict=True and path is invalid.
        """
        result = config.copy()

        for key, value in patch.items():
            if "." in key:
                self._set_nested(result, key, value, strict)
            else:
                result[key] = value

        return result

    def _set_nested(
        self,
        config: dict[str, Any],
        path: str,
        value: Any,
        strict: bool = False,
    ) -> None:
        """Set a nested value using dot notation.

        Args:
            config: Configuration dictionary.
            path: Dot-separated path (e.g., "train.lr").
            value: Value to set.
            strict: If True, raise error for invalid paths.

        Raises:
            ValueError: If strict=True and path is invalid.
        """
        parts = path.split(".")
        current = config

        # Navigate to the parent of the target
        for part in parts[:-1]:
            if part not in current:
                if strict:
                    raise ValueError(f"Invalid path: {path} (key '{part}' not found)")

                # Create intermediate dictionary
                current[part] = {}

            if not isinstance(current[part], dict):
                if strict:
                    raise ValueError(f"Invalid path: {path} ('{part}' is not a dictionary)")

                current[part] = {}

            current = current[part]

        # Set the final value
        target_key = parts[-1]
        current[target_key] = value

    def get_value(
        self,
        config: dict[str, Any],
        path: str,
        default: Any = None,
    ) -> Any:
        """Get a value from a nested configuration using dot notation.

        Args:
            config: Configuration dictionary.
            path: Dot-separated path (e.g., "train.lr").
            default: Default value if path not found.

        Returns:
            Value at path or default.
        """
        parts = path.split(".")
        current = config

        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return default

            current = current[part]

        return current

    def remove_value(
        self,
        config: dict[str, Any],
        path: str,
        strict: bool = False,
    ) -> dict[str, Any]:
        """Remove a value from a nested configuration using dot notation.

        Args:
            config: Configuration dictionary.
            path: Dot-separated path (e.g., "train.lr").
            strict: If True, raise error for invalid paths.

        Returns:
            Updated configuration.

        Raises:
            ValueError: If strict=True and path is invalid.
        """
        result = config.copy()
        parts = path.split(".")
        current = result

        # Navigate to the parent of the target
        for part in parts[:-1]:
            if not isinstance(current, dict) or part not in current:
                if strict:
                    raise ValueError(f"Invalid path: {path} (key '{part}' not found)")

                return result

            current = current[part]

            if not isinstance(current, dict):
                if strict:
                    raise ValueError(f"Invalid path: {path} ('{part}' is not a dictionary)")

                return result

        # Remove the final value
        target_key = parts[-1]
        if isinstance(current, dict) and target_key in current:
            del current[target_key]

        return result

    def merge_configs(
        self,
        base: dict[str, Any],
        override: dict[str, Any],
    ) -> dict[str, Any]:
        """Deep merge two configuration dictionaries.

        Args:
            base: Base configuration.
            override: Override configuration.

        Returns:
            Merged configuration.
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self.merge_configs(result[key], value)
            else:
                # Override with new value
                result[key] = value

        return result

    def flatten_config(
        self,
        config: dict[str, Any],
        prefix: str = "",
    ) -> dict[str, Any]:
        """Flatten a nested configuration dictionary.

        Args:
            config: Configuration dictionary.
            prefix: Prefix for keys.

        Returns:
            Flattened configuration with dot-notation keys.
        """
        result = {}

        for key, value in config.items():
            new_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                result.update(self.flatten_config(value, new_key))
            else:
                result[new_key] = value

        return result

    def unflatten_config(
        self,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Unflatten a configuration dictionary with dot-notation keys.

        Args:
            config: Flattened configuration.

        Returns:
            Nested configuration.
        """
        result = {}

        for key, value in config.items():
            if "." in key:
                self._set_nested(result, key, value, strict=False)
            else:
                result[key] = value

        return result

    def validate_patch(
        self,
        config: dict[str, Any],
        patch: dict[str, Any],
    ) -> list[str]:
        """Validate a patch against a configuration.

        Args:
            config: Configuration dictionary.
            patch: Patch to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        for key in patch.keys():
            if "." in key:
                parts = key.split(".")
                current = config

                # Navigate to the parent of the target
                for part in parts[:-1]:
                    if not isinstance(current, dict) or part not in current:
                        errors.append(f"Invalid path: {key} (key '{part}' not found)")
                        break

                    if not isinstance(current[part], dict):
                        errors.append(f"Invalid path: {key} ('{part}' is not a dictionary)")
                        break

                    current = current[part]

        return errors
