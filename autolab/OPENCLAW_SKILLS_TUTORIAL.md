# OpenClaw Skills Tutorial: Complete Guide

This tutorial teaches you how to create and integrate custom OpenClaw skills with Autolab for autonomous ML research.

## Table of Contents

1. [What are OpenClaw Skills?](#what-are-openclaw-skills)
2. [Skill Structure](#skill-structure)
3. [Required Functions](#required-functions)
4. [Skill Types](#skill-types)
5. [Creating Your First Skill](#creating-your-first-skill)
6. [Advanced Skill Patterns](#advanced-skill-patterns)
7. [Best Practices](#best-practices)
8. [Testing Skills](#testing-skills)
9. [Integrating with Agents](#integrating-with-agents)

---

## What are OpenClaw Skills?

OpenClaw skills are Python functions that extend Autolab's capabilities. They act as tools that the AI agent can call to perform specific actions.

**Key characteristics:**
- **Callable by AI**: The planner (GLM-4.7 or Claude) can invoke them
- **Standardized interface**: All skills follow the same pattern
- **Self-documenting**: Each skill provides its own specification
- **Safe and validated**: Parameters are validated before execution

**Example uses:**
- Create experiments
- Retrieve data (history, goals, results)
- Modify configurations
- Run analysis (compare experiments)
- Generate reports

---

## Skill Structure

Every OpenClaw skill lives in a dedicated directory:

```
autolab/openclaw/skills/
└── autolab_your_skill_name/
    ├── __init__.py          # (can be empty)
    └── skill.py            # Main skill implementation
```

**Naming convention:**
- All skills start with `autolab_` prefix
- Use snake_case: `autolab_create_experiment`
- Directory and skill name match

---

## Required Functions

Every skill **must** implement two functions:

### 1. `execute(args: dict) -> dict`

The main execution function called by the AI agent.

```python
def execute(args: dict) -> dict:
    """Execute the skill.

    Args:
        args: Dictionary of parameters from AI agent

    Returns:
        Dictionary with success status and results/errors
    """
    # Your implementation here
    return {
        "success": True,
        "result": ...
    }
```

**Return format:**
```python
# Success
{
    "success": True,
    "result": ...,           # Your data
    "additional_info": ...  # Optional extra info
}

# Error
{
    "success": False,
    "error": "Error message describing what went wrong"
}
```

### 2. `get_spec() -> dict`

Returns the skill specification for the AI agent.

```python
def get_spec() -> dict:
    """Get skill specification.

    Returns:
        Dictionary describing the skill interface.
    """
    return {
        "name": "autolab_your_skill",
        "description": "What this skill does",
        "parameters": {
            "type": "object",
            "properties": {
                # Parameter definitions
            },
            "required": ["param1", "param2"]
        }
    }
```

**Specification format (JSON Schema):**
```python
{
    "name": "skill_name",              # Unique identifier
    "description": "Skill description", # What the skill does
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Parameter description",
                "default": "default_value"
            },
            "param2": {
                "type": "number",
                "description": "Another parameter"
            }
        },
        "required": ["param1"]  # List of required params
    }
}
```

---

## Skill Types

### Type 1: Data Retrieval Skills

Skills that fetch data from storage.

**Example:** `autolab_get_goal`

```python
"""OpenClaw skill: autolab_get_goal"""

import json
from pathlib import Path


def execute(args: dict) -> dict:
    """Get the current research goal."""
    workspace_path = args.get("workspace_path", "./autolab_workspace")

    # Load state
    from autolab.storage.state_store import StateStore
    state_store = StateStore(workspace_path)
    global_state = state_store.load_global_state()

    goal = global_state.goal

    return {
        "success": True,
        "goal": {
            "title": goal.title,
            "description": goal.description,
            "objectives": goal.objectives,
            "constraints": goal.constraints,
        },
    }


def get_spec() -> dict:
    """Get skill specification."""
    return {
        "name": "autolab_get_goal",
        "description": "Get the current research goal",
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

**Key characteristics:**
- Read-only operations
- Query storage layers
- Return data as JSON

---

### Type 2: Action Skills

Skills that perform actions and modify state.

**Example:** `autolab_create_experiment`

```python
"""OpenClaw skill: autolab_create_experiment"""

from datetime import datetime
from autolab.schemas.experiment import Experiment
from autolab.storage.experiment_store import ExperimentStore


def execute(args: dict) -> dict:
    """Create a new experiment."""
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    title = args.get("title")
    description = args.get("description")
    objective = args.get("objective")

    # Validate required fields
    if not title or not description or not objective:
        return {
            "success": False,
            "error": "Missing required fields: title, description, objective",
        }

    # Load experiment store
    experiment_store = ExperimentStore(workspace_path)

    # Check for duplicate
    all_experiments = experiment_store.load_all()
    for exp in all_experiments.values():
        if exp.title == title:
            return {
                "success": False,
                "error": f"Experiment with title '{title}' already exists",
            }

    # Generate ID
    exp_id = f"exp_{len(all_experiments) + 1:04d}"

    # Create experiment
    experiment = Experiment(
        id=exp_id,
        title=title,
        description=description,
        objective=objective,
        status="pending",
        priority=args.get("priority", 1.0),
        created_at=datetime.utcnow().isoformat() + "Z",
    )

    # Save
    try:
        experiment_store.add(experiment)
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
        }

    return {
        "success": True,
        "experiment": {
            "experiment_id": experiment.id,
            "title": experiment.title,
            "status": experiment.status,
        },
    }


def get_spec() -> dict:
    """Get skill specification."""
    return {
        "name": "autolab_create_experiment",
        "description": "Create a new experiment",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Experiment title"},
                "description": {"type": "string", "description": "Description"},
                "objective": {"type": "string", "description": "Objective"},
                "priority": {
                    "type": "number",
                    "description": "Priority",
                    "default": 1.0,
                },
            },
            "required": ["title", "description", "objective"],
        },
    }
```

**Key characteristics:**
- Modify state (create, update, delete)
- Validate inputs
- Handle errors gracefully
- Return confirmation with new state

---

### Type 3: Analysis Skills

Skills that compute and analyze data.

**Example:** `autolab_compare_experiments`

```python
"""OpenClaw skill: autolab_compare_experiments"""

from autolab.evaluator.comparator import Comparator
from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.result_store import ResultStore


def execute(args: dict) -> dict:
    """Compare experiments."""
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    experiment_id = args.get("experiment_id")
    baseline_id = args.get("baseline_id")

    if not experiment_id:
        return {
            "success": False,
            "error": "experiment_id is required",
        }

    # Load data
    result_store = ResultStore(workspace_path)
    experiment_store = ExperimentStore(workspace_path)

    results = result_store.load_all()
    experiments = experiment_store.load_all()

    current = results.get(experiment_id)
    if not current:
        return {
            "success": False,
            "error": f"Experiment {experiment_id} has no results",
        }

    # Compare
    if baseline_id:
        baseline = results.get(baseline_id)
        comparison = Comparator().compare(current, baseline)
        return {
            "success": True,
            "comparison": comparison.model_dump(),
        }

    return {
        "success": False,
        "error": "baseline_id is required",
    }


def get_spec() -> dict:
    """Get skill specification."""
    return {
        "name": "autolab_compare_experiments",
        "description": "Compare experiment results",
        "parameters": {
            "type": "object",
            "properties": {
                "experiment_id": {
                    "type": "string",
                    "description": "Current experiment ID",
                },
                "baseline_id": {
                    "type": "string",
                    "description": "Baseline ID",
                },
            },
            "required": ["experiment_id"],
        },
    }
```

**Key characteristics:**
- Read data from multiple sources
- Perform computations
- Return analyzed results

---

## Creating Your First Skill

Let's create a custom skill: `autolab_search_experiments` that searches experiments by title or tags.

### Step 1: Create Directory Structure

```bash
cd autolab/openclaw/skills
mkdir -p autolab_search_experiments
cd autolab_search_experiments
touch __init__.py
touch skill.py
```

### Step 2: Implement `execute()` Function

```python
# skill.py

"""OpenClaw skill: autolab_search_experiments

Search experiments by title or tags.
"""

import re
from autolab.storage.experiment_store import ExperimentStore


def execute(args: dict) -> dict:
    """Search experiments by title or tags.

    Args:
        args: Arguments dictionary.

    Returns:
        Dictionary with matching experiments.
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    title_query = args.get("title_query")
    tags = args.get("tags", [])
    status = args.get("status")
    family = args.get("family")
    limit = args.get("limit", 20)

    # Load experiments
    experiment_store = ExperimentStore(workspace_path)
    all_experiments = experiment_store.load_all()

    # Filter experiments
    results = []
    for exp_id, exp in all_experiments.items():
        # Filter by status
        if status and exp.status != status:
            continue

        # Filter by family
        if family and exp.family != family:
            continue

        # Filter by title (substring match, case-insensitive)
        if title_query:
            if title_query.lower() not in exp.title.lower():
                continue

        # Filter by tags (must match at least one)
        if tags and exp.tags:
            if not any(tag in exp.tags for tag in tags):
                continue

        results.append({
            "experiment_id": exp.id,
            "title": exp.title,
            "description": exp.description,
            "status": exp.status,
            "family": exp.family,
            "objective": exp.objective,
            "priority": exp.priority,
            "created_at": exp.created_at,
        })

    # Apply limit
    results = results[:limit]

    return {
        "success": True,
        "count": len(results),
        "experiments": results,
    }


def get_spec() -> dict:
    """Get skill specification."""
    return {
        "name": "autolab_search_experiments",
        "description": "Search experiments by title, tags, status, or family",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "Path to autolab workspace",
                    "default": "./autolab_workspace",
                },
                "title_query": {
                    "type": "string",
                    "description": "Substring to search in titles (case-insensitive)",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to filter (experiments must have at least one)",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status (pending, ready, running, completed, failed)",
                    "enum": ["pending", "ready", "running", "completed", "failed"],
                },
                "family": {
                    "type": "string",
                    "description": "Filter by experiment family",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results to return",
                    "default": 20,
                },
            },
            "required": [],
        },
    }
```

### Step 3: Verify the Skill

```bash
cd /root/Claw-Machine-University/autolab

# Test Python syntax
python3 -m py_compile openclaw/skills/autolab_search_experiments/skill.py

# Test spec function
python3 -c "
from autolab.openclaw.skills.autolab_search_experiments.skill import get_spec
import json
print(json.dumps(get_spec(), indent=2))
"
```

Expected output:
```json
{
  "name": "autolab_search_experiments",
  "description": "Search experiments by title, tags, status, or family",
  "parameters": {
    "type": "object",
    "properties": {
      "workspace_path": {
        "type": "string",
        "description": "Path to autolab workspace",
        "default": "./autolab_workspace"
      },
      "title_query": {
        "type": "string",
        "description": "Substring to search in titles (case-insensitive)"
      },
      ...
    },
    "required": []
  }
}
```

### Step 4: Test Execution

```python
python3 << 'EOF'
from autolab.openclaw.skills.autolab_search_experiments.skill import execute
import json

# Test with no filters
result = execute({})
print(json.dumps(result, indent=2))

# Test with status filter
result = execute({"status": "completed", "limit": 5})
print(json.dumps(result, indent=2))
EOF
```

### Step 5: Make Available to AI Agent

The skill is now automatically available! Autolab's controller discovers all skills at runtime.

No registration needed - just create the file and it's ready.

---

## Advanced Skill Patterns

### Pattern 1: Using Multiple Storage Layers

```python
from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.result_store import ResultStore
from autolab.storage.state_store import StateStore


def execute(args: dict) -> dict:
    workspace_path = args.get("workspace_path")

    # Load multiple storage layers
    exp_store = ExperimentStore(workspace_path)
    result_store = ResultStore(workspace_path)
    state_store = StateStore(workspace_path)

    # Access data from all sources
    experiments = exp_store.load_all()
    results = result_store.load_all()
    state = state_store.load()

    # Combine and analyze
    ...

    return {"success": True, "result": ...}
```

### Pattern 2: External API Integration

```python
import requests


def execute(args: dict) -> dict:
    """Call external API."""
    endpoint = args.get("endpoint")
    data = args.get("data", {})

    try:
        response = requests.post(endpoint, json=data, timeout=30)
        response.raise_for_status()

        return {
            "success": True,
            "data": response.json(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"API call failed: {str(e)}",
        }
```

### Pattern 3: File Operations

```python
from pathlib import Path


def execute(args: dict) -> dict:
    """Read or write files."""
    operation = args.get("operation")  # "read" or "write"
    file_path = Path(args.get("file_path"))
    content = args.get("content", "")

    if operation == "read":
        try:
            with open(file_path, "r") as f:
                return {"success": True, "content": f.read()}
        except FileNotFoundError:
            return {"success": False, "error": "File not found"}

    elif operation == "write":
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(content)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "Invalid operation"}
```

### Pattern 4: Async Operations

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor


def execute(args: dict) -> dict:
    """Run async operations."""
    # Create event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(_async_operation(args))
        return {"success": True, "result": result}
    finally:
        loop.close()


async def _async_operation(args: dict) -> dict:
    """Async operation implementation."""
    # Your async code here
    await asyncio.sleep(1)
    return {"data": "complete"}
```

---

## Best Practices

### 1. Always Return Consistent Structure

```python
# Good
return {
    "success": True,
    "result": data,
    "metadata": {"count": len(data)}
}

# Bad
return data  # No success flag
```

### 2. Validate Inputs Early

```python
def execute(args: dict) -> dict:
    # Validate required parameters
    if not args.get("required_param"):
        return {
            "success": False,
            "error": "required_param is required",
        }

    # Validate parameter types
    limit = args.get("limit")
    if limit is not None:
        if not isinstance(limit, int) or limit <= 0:
            return {
                "success": False,
                "error": "limit must be a positive integer",
            }

    # Proceed with logic
    ...
```

### 3. Handle All Exceptions

```python
def execute(args: dict) -> dict:
    try:
        # Your logic here
        result = _do_something(args)
        return {"success": True, "result": result}
    except ValueError as e:
        return {"success": False, "error": f"Validation error: {str(e)}"}
    except FileNotFoundError as e:
        return {"success": False, "error": f"File not found: {str(e)}"}
    except Exception as e:
        # Log the unexpected error
        import logging
        logging.exception("Unexpected error in skill")
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
```

### 4. Use Descriptive Names

```python
# Good
{
    "experiment_id": "exp_001",
    "experiment_count": 10,
    "search_results": [...]
}

# Avoid
{
    "id": "exp_001",
    "cnt": 10,
    "res": [...]
}
```

### 5. Provide Helpful Error Messages

```python
# Good
return {
    "success": False,
    "error": f"Experiment {experiment_id} not found. Available experiments: {', '.join(available_ids)}"
}

# Bad
return {
    "success": False,
    "error": "Not found"
}
```

### 6. Document Your Code

```python
def execute(args: dict) -> dict:
    """Execute skill to search experiments.

    Searches across all experiments using substring matching on titles
    and optional filtering by status, family, and tags.

    Args:
        args: Dictionary containing:
            - workspace_path (str): Path to workspace
            - title_query (str, optional): Substring to search in titles
            - tags (list[str], optional): Filter by tags (OR logic)
            - status (str, optional): Filter by status
            - family (str, optional): Filter by family
            - limit (int, optional): Max results (default: 20)

    Returns:
        Dictionary with:
            - success (bool): Operation success flag
            - count (int): Number of results
            - experiments (list[dict]): Matching experiments

    Example:
        >>> execute({"title_query": "learning rate", "status": "completed"})
        {
            "success": True,
            "count": 3,
            "experiments": [...]
        }
    """
    ...
```

### 7. Use Type Hints

```python
from typing import Dict, List, Any, Optional


def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute skill."""
    ...


def get_spec() -> Dict[str, Any]:
    """Get skill specification."""
    ...
```

---

## Testing Skills

### Unit Testing

```python
# test_skill.py

import unittest
from autolab.openclaw.skills.autolab_search_experiments.skill import (
    execute,
    get_spec,
)


class TestSearchExperiments(unittest.TestCase):
    def test_get_spec(self):
        """Test spec is valid."""
        spec = get_spec()
        self.assertEqual(spec["name"], "autolab_search_experiments")
        self.assertIn("parameters", spec)

    def test_execute_no_filters(self):
        """Test execute with no filters."""
        result = execute({"workspace_path": "./autolab_workspace"})
        self.assertTrue(result["success"])
        self.assertIn("experiments", result)
        self.assertIsInstance(result["experiments"], list)

    def test_execute_with_status_filter(self):
        """Test execute with status filter."""
        result = execute({
            "workspace_path": "./autolab_workspace",
            "status": "completed"
        })
        self.assertTrue(result["success"])
        for exp in result["experiments"]:
            self.assertEqual(exp["status"], "completed")


if __name__ == "__main__":
    unittest.main()
```

Run tests:
```bash
python3 -m pytest test_skill.py -v
```

### Manual Testing

```python
python3 << 'EOF'
from autolab.openclaw.skills.autolab_search_experiments.skill import execute
import json

# Test 1: Empty search
print("Test 1: Empty search")
result = execute({})
print(f"Success: {result['success']}")
print(f"Count: {result.get('count', 0)}")

# Test 2: With filters
print("\nTest 2: With status filter")
result = execute({"status": "completed", "limit": 5})
print(f"Success: {result['success']}")
print(f"Results: {json.dumps(result.get('experiments', []), indent=2)}")
EOF
```

---

## Integrating with Agents

Once your skill is created, it's automatically available to all Autolab agents.

### Default Agent Skills

Autolab includes pre-configured agents:

**Research Scientist:**
- `autolab_get_goal`
- `autolab_get_history`
- `autolab_get_best_results`
- `autolab_create_hypothesis`
- `autolab_create_experiment`

**Experiment Operator:**
- `autolab_get_queue`
- `autolab_get_gpu_status`
- `autolab_dispatch_ready`
- `autolab_rerank_queue`

**Failure Analyst:**
- `autolab_get_failures`
- `autolab_get_history`
- `autolab_patch_config`
- `autolab_patch_code`

**Code Patcher:**
- `autolab_patch_code`

### Custom Agent Configuration

To create a custom agent with your skill:

1. Create agent config:
```bash
cd autolab/openclaw/agent
nano custom_agent.yaml
```

2. Define your agent:
```yaml
name: custom_researcher
description: Custom agent with my skills
temperature: 0.6
max_tokens: 4096

skills:
  - autolab_get_goal
  - autolab_search_experiments  # Your custom skill
  - autolab_create_experiment

system_prompt: |
  You are a specialized researcher. Use the search skill to find
  relevant experiments before creating new ones.

policies:
  max_experiments_per_cycle: 3
  allow_code_patching: false
```

3. Load in controller:
```python
from autolab.planner.openclaw_bridge import OpenClawBridge

bridge = OpenClawBridge(
    api_key="your_key",
    workspace_path="./autolab_workspace"
)

# Agent will automatically have access to all skills
# including your custom ones
```

### How AI Agent Uses Skills

When the AI agent runs:

1. **Load Context**: Gets research goal, history, failures
2. **Read Specs**: Loads `get_spec()` from all skills
3. **Plan**: Decides which skills to call
4. **Execute**: Calls `execute()` with parameters
5. **Process Results**: Uses results for next planning step

**Example conversation:**

```
AI Agent: I need to find experiments related to learning rates.
System: Available skills include autolab_search_experiments.
AI Agent: Let me search for "learning rate".
System: Calling autolab_search_experiments with {"title_query": "learning rate"}
System: Result: 5 experiments found.
AI Agent: Great! Now I'll create a new experiment based on these results.
System: Calling autolab_create_experiment with {...}
```

---

## Summary Checklist

When creating a new OpenClaw skill:

- [ ] Create directory: `autolab/openclaw/skills/autolab_your_skill/`
- [ ] Create `skill.py` with `execute()` and `get_spec()`
- [ ] Create `__init__.py` (can be empty)
- [ ] Return consistent structure: `{"success": True/False, ...}`
- [ ] Validate all input parameters
- [ ] Handle all exceptions gracefully
- [ ] Provide descriptive error messages
- [ ] Document code with docstrings
- [ ] Test with unit tests
- [ ] Test manually with sample inputs
- [ ] Verify syntax with `python3 -m py_compile`
- [ ] Check spec output is valid JSON

---

## Complete Example: Advanced Skill

Here's a complete skill that combines multiple patterns:

```python
"""OpenClaw skill: autolab_analyze_trends

Analyze experiment trends and identify patterns.
"""

import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.result_store import ResultStore


def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze trends across experiments.

    Identifies patterns in experiment results, including:
    - Best performing configurations
    - Trends over time
    - Most common failure reasons
    - Parameter correlations

    Args:
        args: Dictionary containing:
            - workspace_path (str): Path to workspace
            - family (str, optional): Filter by family
            - metric (str): Primary metric to analyze
            - time_window_hours (int, optional): Analyze last N hours

    Returns:
        Dictionary with:
            - success (bool): Operation success
            - best_experiment (dict): Best performing experiment
            - trends (dict): Trend analysis
            - failures (dict): Failure analysis
    """
    workspace_path = args.get("workspace_path", "./autolab_workspace")
    family = args.get("family")
    metric = args.get("metric", "val_accuracy")
    time_window_hours = args.get("time_window_hours", 24)

    try:
        # Load data
        exp_store = ExperimentStore(workspace_path)
        result_store = ResultStore(workspace_path)

        experiments = exp_store.load_all()
        results = result_store.load_all()

        # Filter by family
        if family:
            experiments = {
                k: v for k, v in experiments.items()
                if v.family == family
            }

        # Filter by time window
        if time_window_hours:
            cutoff = datetime.utcnow() - timedelta(hours=time_window_hours)
            experiments = {
                k: v for k, v in experiments.items()
                if datetime.fromisoformat(v.created_at.replace("Z", "")) > cutoff
            }

        if not experiments:
            return {
                "success": False,
                "error": "No experiments found matching criteria",
            }

        # Analyze best experiment
        best = _find_best_experiment(experiments, results, metric)

        # Analyze trends
        trends = _analyze_trends(experiments, results, metric)

        # Analyze failures
        failures = _analyze_failures(experiments, results)

        return {
            "success": True,
            "best_experiment": best,
            "trends": trends,
            "failures": failures,
            "analyzed_count": len(experiments),
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Analysis failed: {str(e)}",
        }


def _find_best_experiment(
    experiments: Dict[str, Any],
    results: Dict[str, Any],
    metric: str
) -> Optional[Dict[str, Any]]:
    """Find best performing experiment."""
    best = None
    best_value = None

    for exp_id, exp in experiments.items():
        result = results.get(exp_id)
        if not result or result.success != True:
            continue

        value = result.metrics.get(metric)
        if value is None:
            continue

        if best_value is None or value > best_value:
            best_value = value
            best = {
                "experiment_id": exp_id,
                "title": exp.title,
                "metric_value": value,
                "config": exp.config_snapshot,
            }

    return best


def _analyze_trends(
    experiments: Dict[str, Any],
    results: Dict[str, Any],
    metric: str
) -> Dict[str, Any]:
    """Analyze trends in experiments."""
    values = []
    for exp_id, exp in experiments.items():
        result = results.get(exp_id)
        if result and result.success:
            value = result.metrics.get(metric)
            if value is not None:
                values.append(value)

    if not values:
        return {"error": "No valid metric values"}

    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "std": statistics.stdev(values) if len(values) > 1 else 0,
        "min": min(values),
        "max": max(values),
        "count": len(values),
    }


def _analyze_failures(
    experiments: Dict[str, Any],
    results: Dict[str, Any]
) -> Dict[str, Any]:
    """Analyze failure patterns."""
    failures = {}
    for exp_id, exp in experiments.items():
        result = results.get(exp_id)
        if result and result.success != True:
            failure_type = result.failure_type or "unknown"
            failures[failure_type] = failures.get(failure_type, 0) + 1

    return {
        "total_failures": sum(failures.values()),
        "by_type": failures,
    }


def get_spec() -> Dict[str, Any]:
    """Get skill specification."""
    return {
        "name": "autolab_analyze_trends",
        "description": "Analyze trends across experiments to identify patterns",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "Path to autolab workspace",
                    "default": "./autolab_workspace",
                },
                "family": {
                    "type": "string",
                    "description": "Filter by experiment family",
                },
                "metric": {
                    "type": "string",
                    "description": "Primary metric to analyze",
                    "default": "val_accuracy",
                },
                "time_window_hours": {
                    "type": "number",
                    "description": "Analyze last N hours (0 for all)",
                    "default": 24,
                },
            },
            "required": [],
        },
    }
```

---

## Next Steps

1. **Practice**: Create a simple skill like `autolab_get_system_info`
2. **Test**: Use manual testing and unit tests
3. **Integrate**: Add to custom agent configuration
4. **Iterate**: Refine based on AI agent usage patterns
5. **Share**: Contribute useful skills to Autolab

For more examples, see:
- `autolab/openclaw/skills/` - All built-in skills
- Autolab GitHub issues - Community skill requests

Happy skill building!
