"""Validation utilities for patches."""

import re
from typing import Any


class PatchValidator:
    """Validate patches before application."""

    def __init__(self, protected_paths: list[str] | None = None) -> None:
        """Initialize patch validator.

        Args:
            protected_paths: List of protected file paths that cannot be modified.
        """
        self.protected_paths = protected_paths or []

    def validate_code_patch(
        self,
        file_path: str,
        patches: list[dict[str, Any]],
    ) -> tuple[bool, list[str]]:
        """Validate code patches.

        Args:
            file_path: Path to file.
            patches: List of patches.

        Returns:
            Tuple of (is_valid, errors).
        """
        errors = []

        # Check if file is protected
        if self._is_protected(file_path):
            errors.append(f"File is protected: {file_path}")
            return False, errors

        # Validate each patch
        for i, patch in enumerate(patches):
            patch_errors = self._validate_code_patch_structure(patch)

            for error in patch_errors:
                errors.append(f"Patch {i}: {error}")

        return len(errors) == 0, errors

    def _validate_code_patch_structure(
        self,
        patch: dict[str, Any],
    ) -> list[str]:
        """Validate structure of a single code patch.

        Args:
            patch: Patch dictionary.

        Returns:
            List of validation errors.
        """
        errors = []
        patch_type = patch.get("type", "replace")

        if patch_type not in ["replace", "insert_after", "insert_before", "delete"]:
            errors.append(f"Unknown patch type: {patch_type}")
            return errors

        if patch_type == "replace":
            if not patch.get("old_text"):
                errors.append("Replace patch requires 'old_text'")
            if patch.get("new_text") is None:
                errors.append("Replace patch requires 'new_text'")

        elif patch_type in ["insert_after", "insert_before"]:
            if not patch.get("anchor_text"):
                errors.append("Insert patch requires 'anchor_text'")
            if patch.get("new_text") is None:
                errors.append("Insert patch requires 'new_text'")

        elif patch_type == "delete":
            if not patch.get("text_to_delete"):
                errors.append("Delete patch requires 'text_to_delete'")

        return errors

    def validate_config_patch(
        self,
        config: dict[str, Any],
        patch: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate config patch.

        Args:
            config: Original config.
            patch: Patch to apply.

        Returns:
            Tuple of (is_valid, errors).
        """
        errors = []

        for key in patch.keys():
            if "." in key:
                # Validate nested path
                parts = key.split(".")
                current = config

                for part in parts[:-1]:
                    if not isinstance(current, dict):
                        errors.append(f"Invalid path: {key} (cannot traverse non-dict)")
                        break

                    if part not in current:
                        errors.append(f"Invalid path: {key} (key '{part}' not found)")
                        break

                    current = current[part]

        return len(errors) == 0, errors

    def validate_python_code(
        self,
        code: str,
    ) -> tuple[bool, str | None]:
        """Validate Python code syntax.

        Args:
            code: Python code.

        Returns:
            Tuple of (is_valid, error_message).
        """
        import ast

        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"

    def validate_yaml(
        self,
        yaml_str: str,
    ) -> tuple[bool, str | None]:
        """Validate YAML syntax.

        Args:
            yaml_str: YAML string.

        Returns:
            Tuple of (is_valid, error_message).
        """
        import yaml

        try:
            yaml.safe_load(yaml_str)
            return True, None
        except yaml.YAMLError as e:
            return False, str(e)

    def validate_json(
        self,
        json_str: str,
    ) -> tuple[bool, str | None]:
        """Validate JSON syntax.

        Args:
            json_str: JSON string.

        Returns:
            Tuple of (is_valid, error_message).
        """
        import json

        try:
            json.loads(json_str)
            return True, None
        except json.JSONDecodeError as e:
            return False, f"Line {e.lineno}, Column {e.colno}: {e.msg}"

    def _is_protected(self, file_path: str) -> bool:
        """Check if file path is protected.

        Args:
            file_path: File path to check.

        Returns:
            True if protected.
        """
        for protected in self.protected_paths:
            if file_path.startswith(protected):
                return True

        return False

    def validate_no_import_changes(
        self,
        original_code: str,
        patched_code: str,
    ) -> tuple[bool, list[str]]:
        """Validate that imports have not been changed (security check).

        Args:
            original_code: Original code.
            patched_code: Patched code.

        Returns:
            Tuple of (is_valid, errors).
        """
        errors = []

        # Extract imports from both versions
        original_imports = self._extract_imports(original_code)
        patched_imports = self._extract_imports(patched_code)

        # Check for new imports
        new_imports = set(patched_imports) - set(original_imports)

        if new_imports:
            errors.append(f"New imports detected: {', '.join(new_imports)}")

        # Check for removed imports
        removed_imports = set(original_imports) - set(patched_imports)

        if removed_imports:
            errors.append(f"Imports removed: {', '.join(removed_imports)}")

        return len(errors) == 0, errors

    def _extract_imports(self, code: str) -> list[str]:
        """Extract import statements from code.

        Args:
            code: Python code.

        Returns:
            List of import statements.
        """
        imports = []

        # Match 'import module'
        imports.extend(re.findall(r"^import\s+(\S+)", code, re.MULTILINE))

        # Match 'from module import name'
        imports.extend(re.findall(r"^from\s+(\S+)\s+import", code, re.MULTILINE))

        return imports

    def validate_no_exec_eval(
        self,
        code: str,
    ) -> tuple[bool, list[str]]:
        """Validate that code does not contain exec or eval (security check).

        Args:
            code: Code to validate.

        Returns:
            Tuple of (is_valid, errors).
        """
        errors = []

        if re.search(r"\bexec\s*\(", code):
            errors.append("Code contains 'exec()' call")

        if re.search(r"\beval\s*\(", code):
            errors.append("Code contains 'eval()' call")

        if re.search(r"\b__import__\s*\(", code):
            errors.append("Code contains '__import__()' call")

        return len(errors) == 0, errors

    def validate_no_shell_commands(
        self,
        code: str,
    ) -> tuple[bool, list[str]]:
        """Validate that code does not contain shell commands (security check).

        Args:
            code: Code to validate.

        Returns:
            Tuple of (is_valid, errors).
        """
        errors = []

        dangerous_patterns = [
            r"\bos\.system\s*\(",
            r"\bsubprocess\.call\s*\(",
            r"\bsubprocess\.run\s*\(",
            r"\bsubprocess\.Popen\s*\(",
            r"\bcommands\.getoutput\s*\(",
            r"\bpopen\s*\(",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                errors.append(f"Code contains dangerous pattern: {pattern}")

        return len(errors) == 0, errors
