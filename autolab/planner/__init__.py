"""Planner module for experiment planning and OpenClaw integration."""

from autolab.planner.action_router import ActionRouter
from autolab.planner.context_builder import ContextBuilder, PlannerContext
from autolab.planner.openclaw_bridge import MockOpenClawBridge, OpenClawBridge, PlannerResult
from autolab.planner.prompts import (
    get_action_schema,
    get_context_prompt,
    get_experiment_template,
    get_hypothesis_template,
    get_prompt_for_agent,
    PLANNER_SYSTEM_PROMPT,
)

__all__ = [
    "ContextBuilder",
    "PlannerContext",
    "ActionRouter",
    "OpenClawBridge",
    "MockOpenClawBridge",
    "PlannerResult",
    "PLANNER_SYSTEM_PROMPT",
    "get_action_schema",
    "get_context_prompt",
    "get_hypothesis_template",
    "get_experiment_template",
]


def get_prompt_for_agent(agent_type: str) -> str:
    """Get system prompt for a specific agent type.

    Args:
        agent_type: Type of agent.

    Returns:
        System prompt string.
    """
    from autolab.planner.prompts import (
        CODE_PATCHER_PROMPT,
        EXPERIMENT_OPERATOR_PROMPT,
        FAILURE_ANALYST_PROMPT,
        RESEARCH_SCIENTIST_PROMPT,
    )

    prompts = {
        "research_scientist": RESEARCH_SCIENTIST_PROMPT,
        "experiment_operator": EXPERIMENT_OPERATOR_PROMPT,
        "failure_analyst": FAILURE_ANALYST_PROMPT,
        "code_patcher": CODE_PATCHER_PROMPT,
    }

    return prompts.get(agent_type, PLANNER_SYSTEM_PROMPT)
