# Quick Start: Creating Your First OpenClaw Skill

This is a hands-on guide to creating a simple OpenClaw skill in 10 minutes.

## Goal

Create a skill called `autolab_count_experiments` that counts experiments by status.

## Step 1: Create Directory (30 seconds)

```bash
cd autolab/openclaw/skills
mkdir -p autolab_count_experiments
cd autolab_count_experiments
touch __init__.py
touch skill.py
```

## Step 2: Write the Skill (5 minutes)

Edit `skill.py`:

```python
"""OpenClaw skill: autolab_count_experiments

Count experiments by status.
"""

from autolab.storage.experiment_store import ExperimentStore


def execute(args: dict) -> dict:
    """Count experiments by status.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with experiment counts.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")

    # Load experiments
    experiment_store = ExperimentStore(workspace_path)
    experiments = experiment_store.load_all()

    # Count by status
    counts = {}
    for exp in experiments.values():
        status = exp.status
        counts[status] = counts.get(status, 0) + 1

    return {
        "success": True,
        "total": len(experiments),
        "counts": counts,
    }


def get_spec() -> dict:
    """Get skill specification."""
    return {
        "name": "autolab_count_experiments",
        "description": "Count experiments by status",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "Path to autolab workspace",
                    "default": "./autolab_workspace",
                },
            },
            "required": [],
        },
    }
```

## Step 3: Verify Syntax (30 seconds)

```bash
cd /root/Claw-Machine-University/autolab
python3 -m py_compile openclaw/skills/autolab_count_experiments/skill.py
```

If no output, your skill is valid!

## Step 4: Test the Skill (2 minutes)

```python
python3 << 'EOF'
from autolab.openclaw.skills.autolab_count_experiments.skill import execute
import json

# Test execution
result = execute()
print(json.dumps(result, indent=2))

# Test spec
from autolab.openclaw.skills.autolab_count_experiments.skill import get_spec
print("\nSkill Spec:")
print(json.dumps(get_spec(), indent=2))
EOF
```

Expected output:
```json
{
  "success": true,
  "total": 0,
  "counts": {}
}

Skill Spec:
{
  "name": "autolab_count_experiments",
  "description": "Count experiments by status",
  "parameters": {
    "type": "object",
    "properties": {
      "workspace_path": {
        "type": "string",
        "description": "Path to autolab workspace",
        "default": "./autolab_workspace"
      }
    },
    "required": []
  }
}
```

## Step 5: Use It in Autolab (2 minutes)

Your skill is now automatically available! The AI agent can use it.

To test it works in the controller:

```bash
# Create some test experiments first
python3 << 'EOF'
from autolab.storage.experiment_store import ExperimentStore
from autolab.schemas.experiment import Experiment
from datetime import datetime

store = ExperimentStore("./autolab_workspace")

# Add test experiments
store.add(Experiment(
    id="exp_0001",
    title="Test 1",
    description="Test",
    objective="test",
    status="pending",
    priority=1.0,
    created_at=datetime.utcnow().isoformat() + "Z",
))

store.add(Experiment(
    id="exp_0002",
    title="Test 2",
    description="Test",
    objective="test",
    status="completed",
    priority=1.0,
    created_at=datetime.utcnow().isoformat() + "Z",
))

print("Test experiments created")
EOF

# Test your skill
python3 << 'EOF'
from autolab.openclaw.skills.autolab_count_experiments.skill import execute
import json

result = execute()
print(json.dumps(result, indent=2))
EOF
```

Output:
```json
{
  "success": true,
  "total": 2,
  "counts": {
    "pending": 1,
    "completed": 1
  }
}
```

## Step 6: Make Skill Available to Agent (optional)

The skill is already available to all agents. To verify it's being used:

```bash
# Run controller with verbose mode
python3 -m autolab.controller.main --once --verbose

# Look for logs showing:
# [2025-03-09 10:00:00] Loaded 14 skills including autolab_count_experiments
```

## Summary

You just created your first OpenClaw skill! Here's what you learned:

✅ **Skill Structure**: Directory with `skill.py` and `__init__.py`
✅ **Two Functions**: `execute(args)` does the work, `get_spec()` describes it
✅ **Consistent Returns**: Always return `{"success": True/False, ...}`
✅ **Auto-discovery**: Autolab finds skills automatically
✅ **AI Ready**: The agent can now call your skill

## What's Next?

1. **Add More Features**: Add filtering by family, date range, tags
2. **Create Complex Skills**: Build skills that analyze data or call APIs
3. **Learn Best Practices**: Read the full tutorial `OPENCLAW_SKILLS_TUTORIAL.md`
4. **Contribute**: Share useful skills with the community

## Quick Reference

**Skill Template:**

```python
"""OpenClaw skill: autolab_your_skill

Description here.
"""

def execute(args: dict) -> dict:
    """Execute the skill.

    Args:
        args: Arguments from AI.

    Returns:
        Dictionary with results.
    """
    # 1. Get parameters
    param1 = args.get("param1", "default")

    # 2. Validate inputs
    if not param1:
        return {"success": False, "error": "param1 is required"}

    # 3. Do work
    result = do_something(param1)

    # 4. Return
    return {"success": True, "result": result}


def get_spec() -> dict:
    """Get skill specification."""
    return {
        "name": "autolab_your_skill",
        "description": "What this skill does",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Parameter description",
                    "default": "default",
                },
            },
            "required": ["param1"],
        },
    }
```

**Command Checklist:**

```bash
# Create skill
mkdir -p autolab/openclaw/skills/autolab_your_skill
cd autolab/openclaw/skills/autolab_your_skill
touch __init__.py skill.py

# Verify syntax
python3 -m py_compile skill.py

# Test execution
python3 -c "from skill import execute; print(execute())"

# Verify spec
python3 -c "from skill import get_spec; print(get_spec())"

# Done! No registration needed.
```

**Happy Skill Building!** 🚀
