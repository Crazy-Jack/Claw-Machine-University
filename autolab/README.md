# Autolab - Autonomous ML Experiment Framework

A production-grade autonomous ML research system that integrates OpenClaw for planning with deterministic orchestration for experiment management on remote GPU workers.

## Architecture

```
OpenClaw Agent Layer (Planning & Tool Use)
    ↓
Autolab Controller/Policy Layer (Validation & Orchestration)
    ↓
Queue / Scheduler / Evaluator / Stores
    ↓
SSH GPU Workers (Execution)
```

### Core Principles

- **OpenClaw decides**: Multi-step reasoning, hypothesis generation, action planning
- **Autolab validates**: Policy enforcement, action validation, orchestration
- **Executor runs**: SSH/local execution, monitoring, timeout handling
- **Storage remembers**: Persistent state, experiment history, metrics

## Features

- **Continuous autonomous operation**: Runs indefinitely in tmux or daemon mode
- **Remote GPU workers**: SSH-based execution on A100/H100 clusters
- **Structured actions**: JSON-based planner outputs, no arbitrary shell execution
- **Restart-safe**: All state persisted to disk, controller can reconstruct running jobs
- **Research intelligence**: Hypotheses, comparison against baselines, failure analysis
- **Safe patching**: Config patching by default, guarded code patching opt-in
- **Comprehensive reporting**: Per-experiment markdown summaries, periodic lab reports

## Quick Start

### Installation

```bash
cd autolab
pip install -e .
```

### Choosing an AI Provider

Autolab supports two AI providers for autonomous planning:

**1. OpenClaw (Anthropic Claude)** - Default
- Powerful reasoning with Claude models
- Requires Anthropic API key
- Configured in `configs/openclaw.yaml`

**2. Zai GLM-4.7** - Alternative
- High-performance Chinese model
- Requires Zai API key
- Configured in `configs/openclaw.yaml`

To switch providers, edit `configs/openclaw.yaml`:

```yaml
# Choose provider: "anthropic" or "zai"
provider: "anthropic"  # or "zai"

# Anthropic settings
anthropic_api_key: "your_anthropic_key"
anthropic_model: "claude-sonnet-4-20250514"

# Zai settings
zai_api_key: "your_zai_key"
zai_model: "glm-4.7"
zai_base_url: "https://open.bigmodel.cn/api/paas/v4/"
```

Or set environment variables:
```bash
# For Anthropic (Claude)
export ANTHROPIC_API_KEY="your_anthropic_key"

# For Zai (GLM-4.7)
export ZAI_API_KEY="your_zai_key"
```

### Configuration

1. Edit `configs/gpu.yaml` to add your SSH GPU workers
2. Set research goals in workspace or via `autolab set-goal`
3. Configure policies in `configs/policies.yaml`

### Running the Controller

```bash
# Start the main orchestration loop
python -m autolab.controller.main

# Or run in tmux for continuous operation
tmux new -s autolab
python -m autolab.controller.main
```

### CLI Tools

```bash
# View experiment history
python -m autolab.tools.show_history

# Show the experiment queue
python -m autolab.tools.show_queue

# Rerun a failed experiment
python -m autolab.tools.rerun_experiment --id exp_0101

# Export a summary report
python -m autolab.tools.export_summary

# Check worker status
python -m autolab.tools.check_workers

# List recent failures
python -m autolab.tools.list_failures

# Generate a cycle report
python -m autolab.tools.generate_cycle_report
```

## Directory Structure

```
autolab/
├── controller/      # Main orchestration loop, policies, validation
├── planner/         # OpenClaw bridge, context builder, action router
├── executor/        # Job runner, GPU scheduler, SSH runner, monitoring
├── evaluator/       # Metric parsing, comparison, failure analysis
├── patcher/         # Config/code patching with validation
├── storage/         # State, experiment, artifact stores
├── reporting/       # Markdown/JSON reports, dashboard data
├── tools/           # CLI utilities
├── schemas/         # Pydantic models
├── configs/         # System configuration files
├── workspace/       # Running state, logs, artifacts
└── openclaw/        # Skill wrappers and agent configs
```

## AI Provider Integration

Autolab supports two AI providers for autonomous planning: **OpenClaw (Anthropic Claude)** and **Zai GLM-4.7**.

### Using GLM-4.7 (Zai)

GLM-4.7 is a high-performance model from Zhipu AI that excels at research planning and reasoning.

#### Setup GLM-4.7

**1. Get API Key:**
- Visit [Zhipu AI Platform](https://open.bigmodel.cn/)
- Create an account and obtain your API key

**2. Configure Provider:**

```bash
# Set environment variable (recommended)
export ZAI_API_KEY="your_zai_api_key_here"

# Or edit configs/openclaw.yaml
nano configs/openclaw.yaml
```

**3. Update Config File:**

```yaml
# Choose provider
provider: "zai"

# Zai (GLM-4.7) Configuration
zai_api_key: "your_zai_api_key"  # Or use ZAI_API_KEY env var
zai_model: "glm-4.7"
zai_base_url: "https://open.bigmodel.cn/api/paas/v4/"
```

**4. Install Dependencies:**

```bash
# Zai SDK is included in dependencies
pip install -e .
```

**5. Test Connection:**

```python
from zai import ZaiClient

client = ZaiClient(api_key="your_zai_api_key")
response = client.chat.completions.create(
    model="glm-4.7",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

#### GLM-4.7 Advantages

- **Strong reasoning**: Excellent at complex planning tasks
- **Cost-effective**: Competitive pricing vs other providers
- **Fast inference**: Low latency for rapid iteration
- **Chinese support**: Native Chinese language understanding

#### Switching Between Providers

You can switch between Anthropic and Zai at any time:

```bash
# Switch to GLM-4.7
# Edit configs/openclaw.yaml
provider: "zai"

# Set API key
export ZAI_API_KEY="your_zai_key"

# Run controller
python -m autolab.controller.main --verbose

# Switch back to Claude
# Edit configs/openclaw.yaml
provider: "anthropic"

# Set API key
export ANTHROPIC_API_KEY="your_anthropic_key"

# Run controller
python -m autolab.controller.main --verbose
```

### OpenClaw Integration

Autolab provides a complete set of OpenClaw skill wrappers that enable autonomous ML research planning and execution.

### Available Skills

Autolab provides 13 OpenClaw skills organized into categories:

**Information Gathering:**
- `autolab_get_goal` - Read research objectives from workspace
- `autolab_get_history` - Inspect experiment history with filtering
- `autolab_get_best_results` - Find best performing runs by family/metric
- `autolab_get_failures` - Analyze failed experiments with grouping
- `autolab_get_gpu_status` - Check worker availability and GPU status

**Planning & Creation:**
- `autolab_create_hypothesis` - Propose research hypotheses with rationale
- `autolab_create_experiment` - Queue new experiments with full config

**Modification & Control:**
- `autolab_patch_config` - Modify configuration safely with dot notation
- `autolab_patch_code` - Propose guarded code changes with validation
- `autolab_stop_branch` - Stop experiments in a branch (Phase 2)

**Execution & Reporting:**
- `autolab_dispatch_ready` - Launch queued experiments to workers
- `autolab_rerank_queue` - Reorder experiments by priority
- `autolab_generate_report` - Generate summary, experiment, or cycle reports
- `autolab_compare_experiments` - Compare experiments vs baselines or best

### Pre-configured OpenClaw Agents

Autolab includes 4 specialized OpenClaw agent configurations:

1. **Research Scientist** (`research_scientist.yaml`)
   - Temperature: 0.7 (creative but focused)
   - Skills: `autolab_get_goal`, `autolab_get_history`, `autolab_get_best_results`, `autolab_create_hypothesis`, `autolab_create_experiment`
   - Purpose: Generates hypotheses and designs experiments based on results

2. **Experiment Operator** (`experiment_operator.yaml`)
   - Temperature: 0.3 (precise and efficient)
   - Skills: `autolab_get_queue`, `autolab_get_gpu_status`, `autolab_dispatch_ready`, `autolab_rerank_queue`
   - Purpose: Manages queue and dispatches experiments to workers

3. **Failure Analyst** (`failure_analyst.yaml`)
   - Temperature: 0.5 (analytical)
   - Skills: `autolab_get_failures`, `autolab_get_history`, `autolab_patch_config`, `autolab_patch_code`
   - Purpose: Analyzes failures and suggests fixes (config or code patches)

4. **Code Patcher** (`code_patcher.yaml`)
   - Temperature: 0.2 (very conservative)
   - Skills: `autolab_patch_code` with security validation
   - Purpose: Applies code patches with strict safety constraints
   - Security: No import changes, no exec/eval, no shell commands

### Setting Up AI Integration

#### 1. Choose Your Provider and Configure API

Edit `configs/openclaw.yaml`:

```yaml
# For Anthropic (Claude)
provider: "anthropic"
anthropic_api_key: your_anthropic_api_key_here  # or set ANTHROPIC_API_KEY env var
anthropic_model: "claude-3-5-sonnet-20241022"

# For Zai (GLM-4.7)
provider: "zai"
zai_api_key: your_zai_api_key_here  # or set ZAI_API_KEY env var
zai_model: "glm-4.7"
zai_base_url: "https://open.bigmodel.cn/api/paas/v4/"
```

#### 2. Register Autolab Skills

The Autolab controller automatically registers all skills when it starts. Skills are located in:

```
autolab/openclaw/skills/
├── autolab_get_goal/
│   └── skill.py
├── autolab_create_experiment/
│   └── skill.py
└── ... (13 skills total)
```

Each skill implements:
- `execute(args: dict) -> dict`: Main execution function
- `get_spec() -> dict`: Returns skill specification

#### 3. Choose Integration Mode

**Mode 1: Controller-Driven (Recommended)**

Autolab's main controller orchestrates OpenClaw agents:

```bash
python -m autolab.controller.main
```

The controller:
- Loads global state and experiment history
- Builds context for each agent type
- Calls OpenClaw with appropriate agent config
- Validates and executes proposed actions
- Updates state and repeats

**Mode 2: Direct OpenClaw Calls**

You can also call Autolab skills directly from your own OpenClaw integration:

```python
from autolab.openclaw.skills.autolab_create_experiment.skill import execute

result = execute({
    "title": "Test higher learning rate",
    "description": "Try lr=0.001 instead of 0.0001",
    "objective": "maximize val_accuracy",
    "family": "lr_sweep",
    "config": {
        "train": {
            "lr": 0.001,
            "batch_size": 64
        }
    },
    "script": "train.py",
    "priority": 1.0
})
```

### Complete Workflow Example

Here's a typical autonomous research cycle:

```bash
# 1. Start the controller
python -m autolab.controller.main

# The controller will:
#   a) Load current state and results
#   b) Call Research Scientist agent with recent history
#   c) Research Scientist proposes: "Try lr=0.001 with batch_size=128"
#   d) Controller validates against policies
#   e) New experiment queued with status "pending"
#
#   f) Controller calls Experiment Operator
#   g) Experiment Operator dispatches to available GPU worker
#   h) Job runs on remote worker via SSH
#
#   i) Job completes, metrics parsed
#   j) If failed: Failure Analyst analyzes
#   k) If succeeded: Comparator checks vs baseline
#   l) Research Scientist updated with new results
#
#   m) Loop repeats indefinitely...
```

### Monitoring Progress

While the controller runs autonomously, you can monitor progress:

```bash
# Terminal 1: Controller running
python -m autolab.controller.main

# Terminal 2: Monitor queue
watch -n 10 python -m autolab.tools.show_queue

# Terminal 3: Monitor history
watch -n 30 python -m autolab.tools.show_history --status running

# Terminal 4: Check workers
python -m autolab.tools.check_workers --update

# Terminal 5: View failures
python -m autolab.tools.list_failures
```

### Advanced OpenClaw Usage

#### Custom Agent Configuration

Create your own agent config in `autolab/openclaw/agent/`:

```yaml
# custom_agent.yaml
name: custom_researcher
description: Specialized agent for your research
temperature: 0.6
max_tokens: 4096

skills:
  - autolab_get_goal
  - autolab_get_history
  - autolab_create_experiment

system_prompt: |
  You are a specialized researcher focused on X.
  Always consider Y when proposing experiments.

policies:
  max_experiments_per_cycle: 5
  allow_code_patching: false
```

#### Skill Arguments Reference

**autolab_create_experiment:**
```python
{
    "title": str,              # Experiment title
    "description": str,        # Detailed description
    "objective": str,          # Metric to optimize
    "family": str,             # Experiment family/group
    "config": dict,            # Training configuration
    "script": str,             # Training script path
    "priority": float,         # Queue priority (higher = sooner)
    "tags": list[str],         # Optional tags
    "dependencies": list[str]  # Required completed experiments
}
```

**autolab_patch_config:**
```python
{
    "experiment_id": str,      # Base experiment to modify
    "patches": {               # Config patches (dot notation)
        "train.lr": 0.001,
        "model.hidden_size": 512
    },
    "description": str         # Change description
}
```

**autolab_patch_code:**
```python
{
    "file_path": str,          # File to modify
    "operation": str,          # "replace", "insert_after", "insert_before", "delete"
    "old_text": str,           # Text to replace (for replace/delete)
    "new_text": str,           # New text (for replace/insert)
    "description": str        # Change description
}
```

**autolab_generate_report:**
```python
{
    "report_type": str,        # "summary", "experiment", "cycle"
    "experiment_id": str,      # Required for "experiment" type
    "cycle_number": int,       # Required for "cycle" type
    "output_path": str         # Optional output path
}
```

### Troubleshooting

**Controller fails to start:**
```bash
# Check OpenClaw API key
cat configs/openclaw.yaml

# Verify workers are reachable
python -m autolab.tools.check_workers --update
```

**Experiments not dispatching:**
```bash
# Check queue status
python -m autolab.tools.show_queue

# Check worker availability
python -m autolab.tools.check_workers

# Check policy limits
cat configs/policies.yaml
```

**OpenClaw agent times out:**
```bash
# Increase timeout in configs/openclaw.yaml
# Or reduce experiment history passed to agent
```

**Code patches rejected:**
```bash
# Check patch validation logs
cat workspace/logs/patches.log

# Verify patch policies
cat configs/policies.yaml | grep -A 10 patching
```

## Data Flow

1. Controller loads global state and recent results
2. Context builder compiles research goal, history, failures, queue
3. OpenClaw bridge proposes actions (create experiment, patch config, etc.)
4. Action validator checks against policies and constraints
5. Controller applies validated actions to queue/state
6. Worker manager dispatches ready experiments to GPU servers
7. Process monitor tracks job progress and logs
8. Evaluator parses metrics when jobs complete
9. Comparator computes deltas vs baseline, parent, family best
10. Reporter generates summaries and periodic lab reports
11. Loop repeats with updated state

## Configuration

### GPU Workers (`configs/gpu.yaml`)

```yaml
workers:
  - name: a100x1-001
    host: 34.48.207.147
    user: clawbot-tian
    ssh_key: ~/.ssh/id_ed25519
    gpus:
      - id: "0"
        type: "A100"
        memory_gb: 40
    enabled: true
```

### Policies (`configs/policies.yaml`)

```yaml
planner:
  max_new_experiments_per_cycle: 3
  allow_code_patching: false

executor:
  max_concurrent_jobs: 2
  stall_timeout_minutes: 30

patching:
  allowed_config_paths:
    - train.lr
    - train.batch_size
```

## Safety Features

- **Allowlist-based patching**: Only specific config paths and code files can be modified
- **Protected paths**: Git, secrets, SSH keys cannot be touched
- **Duplicate detection**: Prevents creating identical experiments
- **Bounded retries**: Transient failures only retried limited times
- **Validation**: Python syntax checked before code patches applied
- **Audit trail**: All planner inputs/outputs logged, even invalid ones

## License

MIT
