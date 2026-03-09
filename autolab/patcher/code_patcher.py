"""Code patcher for applying code patches."""

import os
from pathlib import Path
from typing import Any


class CodePatcher:
    """Apply code patches to files using diff-style patches."""

    def __init__(
        self,
        workspace_path: str = "./autolab_workspace",
        validate_syntax: bool = True,
    ) -> None:
        """Initialize code patcher.

        Args:
            workspace_path: Path to workspace directory.
            validate_syntax: Whether to validate Python syntax after patching.
        """
        self.workspace_path = Path(workspace_path).expanduser().resolve()
        self.validate_syntax = validate_syntax

    def apply_patch(
        self,
        file_path: str,
        patches: list[dict[str, Any]],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Apply patches to a file.

        Args:
            file_path: Path to the file to patch.
            patches: List of patch dictionaries.
            dry_run: If True, don't actually apply patches.

        Returns:
            Result dictionary with success status and details.
        """
        full_path = self.workspace_path / file_path

        if not full_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "file_path": file_path,
            }

        # Read original content
        try:
            with open(full_path) as f:
                original_content = f.read()
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read file: {e}",
                "file_path": file_path,
            }

        # Apply patches
        content = original_content
        applied = []
        failed = []

        for i, patch in enumerate(patches):
            patch_type = patch.get("type", "replace")

            if patch_type == "replace":
                result = self._apply_replace_patch(content, patch)
            elif patch_type == "insert_after":
                result = self._apply_insert_after_patch(content, patch)
            elif patch_type == "insert_before":
                result = self._apply_insert_before_patch(content, patch)
            elif patch_type == "delete":
                result = self._apply_delete_patch(content, patch)
            else:
                failed.append({
                    "index": i,
                    "type": patch_type,
                    "error": f"Unknown patch type: {patch_type}",
                })
                continue

            if result["success"]:
                content = result["content"]
                applied.append({
                    "index": i,
                    "type": patch_type,
                })
            else:
                failed.append({
                    "index": i,
                    "type": patch_type,
                    "error": result["error"],
                })

        # Validate syntax if requested
        syntax_error = None
        if self.validate_syntax and not dry_run and full_path.suffix == ".py":
            syntax_error = self._validate_python_syntax(content)

            if syntax_error:
                return {
                    "success": False,
                    "error": f"Syntax error: {syntax_error}",
                    "file_path": file_path,
                    "applied": applied,
                    "failed": failed,
                }

        # Write patched content
        if not dry_run and not syntax_error:
            try:
                # Backup original
                backup_path = full_path.with_suffix(f"{full_path.suffix}.bak")
                with open(backup_path, "w") as f:
                    f.write(original_content)

                # Write patched content
                with open(full_path, "w") as f:
                    f.write(content)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to write file: {e}",
                    "file_path": file_path,
                    "applied": applied,
                    "failed": failed,
                }

        return {
            "success": len(failed) == 0 and not syntax_error,
            "file_path": file_path,
            "applied": applied,
            "failed": failed,
            "backup_path": str(full_path.with_suffix(f"{full_path.suffix}.bak")) if not dry_run else None,
            "dry_run": dry_run,
        }

    def _apply_replace_patch(
        self,
        content: str,
        patch: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply a replace patch.

        Args:
            content: Original content.
            patch: Patch dictionary.

        Returns:
            Result dictionary.
        """
        old_text = patch.get("old_text")
        new_text = patch.get("new_text")

        if not old_text or new_text is None:
            return {
                "success": False,
                "error": "Replace patch requires 'old_text' and 'new_text'",
            }

        if old_text not in content:
            return {
                "success": False,
                "error": f"Old text not found in file: {old_text[:50]}...",
            }

        new_content = content.replace(old_text, new_text)

        return {
            "success": True,
            "content": new_content,
        }

    def _apply_insert_after_patch(
        self,
        content: str,
        patch: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply an insert-after patch.

        Args:
            content: Original content.
            patch: Patch dictionary.

        Returns:
            Result dictionary.
        """
        anchor_text = patch.get("anchor_text")
        new_text = patch.get("new_text")

        if not anchor_text or new_text is None:
            return {
                "success": False,
                "error": "Insert-after patch requires 'anchor_text' and 'new_text'",
            }

        if anchor_text not in content:
            return {
                "success": False,
                "error": f"Anchor text not found in file: {anchor_text[:50]}...",
            }

        new_content = content.replace(anchor_text, anchor_text + new_text)

        return {
            "success": True,
            "content": new_content,
        }

    def _apply_insert_before_patch(
        self,
        content: str,
        patch: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply an insert-before patch.

        Args:
            content: Original content.
            patch: Patch dictionary.

        Returns:
            Result dictionary.
        """
        anchor_text = patch.get("anchor_text")
        new_text = patch.get("new_text")

        if not anchor_text or new_text is None:
            return {
                "success": False,
                "error": "Insert-before patch requires 'anchor_text' and 'new_text'",
            }

        if anchor_text not in content:
            return {
                "success": False,
                "error": f"Anchor text not found in file: {anchor_text[:50]}...",
            }

        new_content = content.replace(anchor_text, new_text + anchor_text)

        return {
            "success": True,
            "content": new_content,
        }

    def _apply_delete_patch(
        self,
        content: str,
        patch: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply a delete patch.

        Args:
            content: Original content.
            patch: Patch dictionary.

        Returns:
            Result dictionary.
        """
        text_to_delete = patch.get("text_to_delete")

        if not text_to_delete:
            return {
                "success": False,
                "error": "Delete patch requires 'text_to_delete'",
            }

        if text_to_delete not in content:
            return {
                "success": False,
                "error": f"Text not found in file: {text_to_delete[:50]}...",
            }

        new_content = content.replace(text_to_delete, "")

        return {
            "success": True,
            "content": new_content,
        }

    def _validate_python_syntax(self, content: str) -> str | None:
        """Validate Python syntax.

        Args:
            content: Python code to validate.

        Returns:
            Error message if invalid, None otherwise.
        """
        import ast

        try:
            ast.parse(content)
            return None
        except SyntaxError as e:
            return f"Line {e.lineno}: {e.msg}"

    def validate_patches(
        self,
        file_path: str,
        patches: list[dict[str, Any]],
    ) -> list[str]:
        """Validate patches without applying them.

        Args:
            file_path: Path to the file.
            patches: List of patch dictionaries.

        Returns:
            List of validation errors.
        """
        full_path = self.workspace_path / file_path
        errors = []

        if not full_path.exists():
            errors.append(f"File not found: {file_path}")
            return errors

        # Read original content
        try:
            with open(full_path) as f:
                content = f.read()
        except Exception as e:
            errors.append(f"Failed to read file: {e}")
            return errors

        # Validate each patch
        for i, patch in enumerate(patches):
            patch_type = patch.get("type", "replace")

            if patch_type == "replace":
                if not patch.get("old_text") or patch.get("new_text") is None:
                    errors.append(f"Patch {i}: Replace patch requires 'old_text' and 'new_text'")

                if patch.get("old_text") not in content:
                    errors.append(f"Patch {i}: Old text not found in file")

            elif patch_type in ["insert_after", "insert_before"]:
                if not patch.get("anchor_text") or patch.get("new_text") is None:
                    errors.append(f"Patch {i}: Insert patch requires 'anchor_text' and 'new_text'")

                if patch.get("anchor_text") not in content:
                    errors.append(f"Patch {i}: Anchor text not found in file")

            elif patch_type == "delete":
                if not patch.get("text_to_delete"):
                    errors.append(f"Patch {i}: Delete patch requires 'text_to_delete'")

                if patch.get("text_to_delete") not in content:
                    errors.append(f"Patch {i}: Text not found in file")

            else:
                errors.append(f"Patch {i}: Unknown patch type '{patch_type}'")

        return errors
