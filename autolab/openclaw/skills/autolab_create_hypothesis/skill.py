"""OpenClaw skill: autolab_create_hypothesis

Create a new research hypothesis.
"""

from datetime import datetime

from autolab.schemas.hypothesis import Hypothesis
from autolab.storage.state_store import StateStore


def execute(args: dict) -> dict:
    """Execute the create_hypothesis skill.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with created hypothesis.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    title = args.get("title")
    rationale = args.get("rationale")
    expected_effect = args.get("expected_effect")
    priority = args.get("priority", 1.0)
    family = args.get("family")
    tags = args.get("tags", [])

    # Validate required fields
    if not title or not rationale or not expected_effect:
        return {
            "success": False,
            "error": "Missing required fields: title, rationale, expected_effect",
        }

    # Load state
    state_store = StateStore(workspace_path)
    hypotheses = state_store.load_hypotheses()

    # Generate hypothesis ID
    hyp_count = len(hypotheses) + 1
    hyp_id = f"hyp_{hyp_count:04d}"

    # Create hypothesis
    hypothesis = Hypothesis(
        id=hyp_id,
        title=title,
        rationale=rationale,
        expected_effect=expected_effect,
        priority=priority,
        related_experiments=[],
        status="active",
        created_by="openclaw",
        created_at=datetime.utcnow().isoformat() + "Z",
        family=family,
        tags=tags,
    )

    # Save
    state_store.add_hypothesis(hypothesis)

    return {
        "success": True,
        "hypothesis": {
            "hypothesis_id": hypothesis.id,
            "title": hypothesis.title,
            "status": hypothesis.status,
            "created_at": hypothesis.created_at,
        },
    }


def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Skill specification dictionary.
    """
    return {
        "name": "autolab_create_hypothesis",
        "description": "Create a new research hypothesis",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "Path to autolab workspace",
                    "default": "./autolab_workspace",
                },
                "title": {
                    "type": "string",
                    "description": "Hypothesis title",
                },
                "rationale": {
                    "type": "string",
                    "description": "Scientific rationale for the hypothesis",
                },
                "expected_effect": {
                    "type": "string",
                    "description": "Expected effect if hypothesis is correct",
                },
                "priority": {
                    "type": "number",
                    "description": "Priority (0-10, higher is more important)",
                    "default": 1.0,
                },
                "family": {
                    "type": "string",
                    "description": "Research family/group",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization",
                },
            },
            "required": ["title", "rationale", "expected_effect"],
        },
    }
