"""OpenClaw skill: autolab_patch_code

Suggest a code patch (requires validation).
"""

import json
from pathlib import Path
from datetime import datetime

from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.git_snapshot import GitSnapshot


def execute(args: dict) -> dict:
    """Execute patch_code skill.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with patch result.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    target_file = args.get("target_file")
    patch_content = args.get("patch_content")
    experiment_id = args.get("experiment_id")
    rationale = args.get("rationale", "")
    validation_required = args.get("validation_required", True)

    # Validate required fields
    if not target_file:
        return {
            "success": False,
            "error": "Missing required field: target_file",
        }

    if not patch_content:
        return {
            "success": False,
            "error": "Missing required field: patch_content",
        }

    # Check if file exists
    file_path = Path(target_file).expanduser().resolve()

    if not file_path.exists():
        return {
            "success": False,
            "error": f"Target file not found: {file_path}",
        }

    # Check if file is in git repo
    git_snapshot = GitSnapshot(".")
    if not git_snapshot.is_git_repo():
        return {
            "success": False,
            "error": "Not in a git repository - code patches require git",
        }

    # Validate patch syntax
    if validation_required:
        syntax_check = _validate_patch_syntax(patch_content)

        if not syntax_check["valid"]:
            return {
                "success": False,
                "error": f"Invalid patch syntax: {syntax_check['error']}",
            }

    # Read original file for diff
    with open(file_path, "r") as f:
        original_content = f.read()

    # Create patch record
    patch_record = {
        "target_file": target_file,
        "patch_content": patch_content,
        "original_content": original_content,
        "rationale": rationale,
        "experiment_id": experiment_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "git_snapshot": git_snapshot.get_snapshot(),
        "validated": not validation_required or syntax_check["valid"],
    }

    # Save patch to patches directory
    patches_dir = Path(workspace_path) / "patches"
    patches_dir.mkdir(parents=True, exist_ok=True)

    patch_id = f"patch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    patch_path = patches_dir / patch_id

    with open(patch_path, "w") as f:
        json.dump(patch_record, f, indent=2)

    return {
        "success": True,
        "patch": {
            "patch_id": patch_id,
            "patch_path": str(patch_path),
            "target_file": target_file,
            "validated": patch_record["validated"],
            "requires_manual_application": True,
            "rationale": rationale,
        },
        "note": "Patch saved but not applied. Requires manual validation and application.",
    }


def _validate_patch_syntax(patch_content: str) -> dict:
    """Validate patch file syntax.

    Args:
        patch_content: Patch content.

    Returns:
        Dictionary with validation result.
    """
    # Check for unified diff format
    if not patch_content.startswith("---") and not patch_content.startswith("diff"):
        return {
            "valid": False,
            "error": "Patch must be in unified diff format",
        }

    # Basic syntax checks
    lines = patch_content.split("\n")
    for i, line in enumerate(lines, 1):
        # Check for common diff markers
        if line.startswith(("+++", "---", "@@", "+", "-", " ")):
            continue

        # Allow context lines
        if line.startswith(("Index:", "=======", "diff ")):
            continue

        # If we get here, line doesn't match expected format
        return {
            "valid": False,
            "error": f"Invalid patch format at line {i}: {line[:50]}",
        }

    return {
        "valid": True,
    }


def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Skill specification dictionary.
    """
    return {
        "name": "autolab_patch_code",
        "description": "Suggest a code patch (requires manual validation before application)",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "Path to autolab workspace",
                    "default": "./autolab_workspace",
                },
                "target_file": {
                    "type": "string",
                    "description": "Path to file to patch (must be in git repo)",
                },
                "patch_content": {
                    "type": "string",
                    "description": "Patch content in unified diff format",
                },
                "experiment_id": {
                    "type": "string",
                    "description": "Associated experiment ID",
                },
                "rationale": {
                    "type": "string",
                    "description": "Reason for the patch",
                },
                "validation_required": {
                    "type": "boolean",
                    "description": "Whether to validate patch syntax",
                    "default": True,
                },
            },
            "required": ["target_file", "patch_content"],
        },
    }
