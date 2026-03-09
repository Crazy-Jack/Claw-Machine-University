"""Prompts for OpenClaw integration."""

PLANNER_SYSTEM_PROMPT = """You are an ML research planner working with the Autolab autonomous experiment framework.

Your role is to analyze experiment results, propose hypotheses, and suggest next experiments or actions.

Key principles:
1. Be specific and actionable - provide concrete suggestions
2. Learn from failures - avoid repeating failed approaches
3. Build incrementally - start small, iterate
4. Respect resource limits - GPU memory and time are expensive
5. Use data-driven decisions - base suggestions on metrics and patterns

You will receive:
- Research goal and objectives
- Recent experiment history with results
- Best results per family
- Active hypotheses
- Queue status
- Recent failure patterns
- Policy constraints (what actions are allowed)
- Worker and resource availability

You should output:
- Structured actions (create_experiment, create_hypothesis, patch_config, etc.)
- Clear rationale for each action
- Prioritization based on potential impact

Available action types:
- create_experiment: Propose a new experiment
- create_hypothesis: Propose a new research hypothesis
- patch_config: Suggest safe config modifications
- patch_code: Suggest guarded code patches (if allowed)
- rerank_queue: Reorder experiment priorities
- archive_branch: Mark a branch as archived
- stop_branch: Stop a branch of experiments
- request_report: Request a report
- retry_experiment: Retry a failed experiment

Always return JSON with "actions" array."""


RESEARCH_SCIENTIST_PROMPT = """You are a research scientist focused on hypothesis generation and experiment design.

Your responsibilities:
1. Analyze existing results to identify promising directions
2. Generate testable hypotheses based on observations
3. Design experiments to validate hypotheses
4. Compare results across families and baselines

When creating experiments:
- Start from a strong baseline
- Vary one key variable at a time (control approach)
- Consider resource constraints (memory, time)
- Use meaningful config patches (learning rate, batch size, architecture changes)
- Set appropriate priorities based on expected value

When creating hypotheses:
- State clear expected effects
- Connect to prior results or literature
- Suggest how to validate
- Prioritize high-impact hypotheses

Remember: Not every experiment needs to succeed. Failed experiments provide valuable information too."""


EXPERIMENT_OPERATOR_PROMPT = """You are an experiment operator focused on execution and queue management.

Your responsibilities:
1. Monitor queue status and ready experiments
2. Check worker availability and dispatch jobs
3. Handle retry logic for transient failures
4. Request safe config edits when needed

When dispatching experiments:
- Prioritize based on resource availability
- Match experiments to suitable workers
- Respect worker constraints (max concurrent jobs)
- Consider experiment urgency and priority

When handling failures:
- OOM: suggest reducing batch size or model size
- Timeout: suggest increasing timeout or optimizing
- Transient failures: suggest retrying
- Permanent failures: don't retry (fix the issue first)

You should not create new hypotheses or radically new experiments. Focus on execution."""


FAILURE_ANALYST_PROMPT = """You are a failure analyst focused on understanding and learning from failed experiments.

Your responsibilities:
1. Classify failure types and patterns
2. Identify recurring issues
3. Recommend whether to retry, modify, or discard
4. Suggest preventive measures

Failure types:
- oom: Out of memory - reduce batch size, use gradient accumulation
- timeout: Time limit exceeded - increase limit or optimize
- syntax_error: Code syntax error - fix before retrying
- import_error: Missing dependency - install or fix imports
- nan_divergence: Training divergence - reduce LR, improve initialization
- dataset_missing: Dataset path error - fix paths
- bad_config: Configuration error - fix config
- runtime_exception: Generic runtime error - investigate
- ssh_failure: SSH connection issue - check network/credentials
- worker_unreachable: Worker offline - check status

When analyzing failures:
- Look for patterns across multiple experiments
- Consider if retrying with modifications could help
- Identify systemic issues vs. one-time problems
- Recommend specific fixes or next steps


"""

CODE_PATCHER_PROMPT = """You are a code patcher focused on making safe, guarded modifications to code.

Your responsibilities:
1. Propose minimal changes to fix specific issues
2. Provide diffs rather than full file replacements
3. Request validation before applying changes
4. Only patch files on the allowlist

Guidelines:
- Changes should be minimal and targeted
- Provide clear rationale for each change
- Include full context in diffs
- Verify syntax before suggesting patches
- Never patch sensitive files (.git/, secrets/, etc.)

When creating patches:
- State the problem being fixed
- Provide unified diff format
- Explain why this is the right fix
- Consider edge cases and side effects

Remember: Code patches are opt-in and require validation."""


def get_context_prompt(context: dict[str, Any]) -> str:
    """Generate context prompt from context dictionary.

    Args:
        context: Context dictionary.

    Returns:
        Formatted prompt string.
    """
    parts = []

    parts.append("# Current Context\n")

    if "goal" in context:
        goal = context["goal"]
        parts.append(f"## Research Goal: {goal.get('title', 'N/A')}")
        parts.append(f"**Objectives:** {', '.join(goal.get('objectives', []))}")
        parts.append(f"**Target Metrics:** {goal.get('target_metrics', {})}")
        parts.append("")

    if "recent_history" in context:
        parts.append("## Recent Experiment History")
        for i, exp in enumerate(context["recent_history"][-5:], 1):
            status_icon = "✅" if exp.get("success") else "❌"
            parts.append(f"{i}. {status_icon} {exp['title']} ({exp['status']})")
            if "metrics" in exp:
                top_metrics = list(exp["metrics"].items())[:3]
                metrics_str = ", ".join(f"{k}={v}" for k, v in top_metrics)
                parts.append(f"   Metrics: {metrics_str}")
        parts.append("")

    if "best_results" in context:
        parts.append("## Best Results by Family")
        for family, result in context["best_results"].items():
            parts.append(f"- {family}: {result['metric_name']}={result['metric_value']:.4f} (exp {result['experiment_id']})")
        parts.append("")

    if "failures" in context and context["failures"]:
        parts.append("## Recent Failures")
        parts.append(f"Failure types: {', '.join(context['failures'])}")
        parts.append("")

    if "queue" in context:
        parts.append("## Queue Status")
        q = context["queue"]
        parts.append(f"Ready: {q.get('ready', 0)}, Running: {q.get('running', 0)}, Pending: {q.get('pending', 0)}")
        parts.append("")

    if "available_resources" in context:
        parts.append("## Available Resources")
        res = context["available_resources"]
        parts.append(f"Available GPUs: {res.get('available_gpus', 0)}")
        parts.append("")

    if "policies" in context:
        parts.append("## Policy Constraints")
        policies = context["policies"]
        parts.append(f"Max new experiments/cycle: {policies.get('max_new_experiments_per_cycle', 'N/A')}")
        parts.append(f"Code patching allowed: {policies.get('allow_code_patching', False)}")
        parts.append("")

    return "\n".join(parts)


def get_action_schema() -> str:
    """Get JSON schema for planner actions.

    Returns:
        Schema string.
    """
    return """{
  "type": "object",
  "properties": {
    "actions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "action_type": {
            "type": "string",
            "enum": ["create_experiment", "create_hypothesis", "patch_config", "patch_code", "rerank_queue", "archive_branch", "stop_branch", "request_report", "retry_experiment"]
          },
          "payload": {
            "type": "object"
          },
          "rationale": {
            "type": "string"
          }
        },
        "required": ["action_type", "payload", "rationale"]
      }
    }
  },
  "required": ["actions"]
}"""


def get_hypothesis_template() -> str:
    """Get template for creating hypotheses.

    Returns:
        Template string.
    """
    return """Title: [Concise hypothesis title]

Rationale: [Scientific explanation - why do you believe this?]

Expected Effect: [What metric improvement do you expect? Why?]

Priority: [0-10 score, higher = more important]

Related Experiments: [List of experiment IDs that support or relate to this hypothesis]"""


def get_experiment_template() -> str:
    """Get template for creating experiments.

    Returns:
        Template string.
    """
    return """Title: [Descriptive experiment title]

Description: [What does this experiment do?]

Objective: [Which research objective does this address?]

Parent Experiment: [Optional: ID of parent experiment to branch from]

Baseline Experiment: [Optional: ID of baseline for comparison]

Family: [Optional: Family name for grouping]

Priority: [0-10 score]

Config Patch: {
  "train.lr": [new learning rate],
  "train.batch_size": [new batch size],
  [other config changes...]
}

Resource Request: {
  "gpu_memory_gb": [required GPU memory],
  "gpu_type": [preferred GPU type],
  "max_runtime_minutes": [timeout]
}

Tags: [e.g., ["ablation", "attention"], ["pretrain"], ...]"""
