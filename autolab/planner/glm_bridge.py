"""GLM-4.7 bridge for integrating with Zai's GLM-4.7 API."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from autolab.planner.context_builder import PlannerContext
from autolab.schemas.action import PlannerAction


class PlannerResult(BaseModel):
    """Result from planner."""

    actions: list[PlannerAction] = Field(..., description="Proposed actions")
    raw_output: str = Field(..., description="Raw planner output")
    timestamp: str = Field(..., description="ISO timestamp")
    model_used: str | None = Field(None, description="Model used for planning")
    tokens_used: dict[str, int] | None = Field(None, description="Token usage")


class GLMBridge:
    """Bridge for communicating with Zai's GLM-4.7 API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "glm-4.7",
        base_url: str = "https://open.bigmodel.cn/api/paas/v4/",
        workspace_path: str = "./autolab_workspace",
    ) -> None:
        """Initialize GLM bridge.

        Args:
            api_key: Zai API key (or use ZAI_API_KEY env var).
            model: Model to use for planning (default: glm-4.7).
            base_url: Base URL for API (Mainland or Overseas).
            workspace_path: Path to workspace for logging.
        """
        import os

        self.api_key = api_key or os.environ.get("ZAI_API_KEY")
        self.model = model
        self.base_url = base_url
        self.workspace_path = Path(workspace_path).expanduser().resolve()
        self.raw_output_dir = self.workspace_path / "planner_raw"
        self.raw_output_dir.mkdir(parents=True, exist_ok=True)

        # Lazy import zai
        try:
            from zai import ZaiClient

            self.client = ZaiClient(api_key=self.api_key, base_url=self.base_url)
        except ImportError:
            self.client = None
            print("Warning: zai package not installed. Bridge will be a no-op.")
            print("Install with: pip install zai-sdk")

    def propose_actions(
        self,
        context: PlannerContext,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> PlannerResult:
        """Propose actions based on context.

        Args:
            context: Planner context.
            system_prompt: Optional system prompt override.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            PlannerResult object.
        """
        if self.client is None:
            # Return empty result if no client
            return PlannerResult(
                actions=[],
                raw_output="GLM client not available - install zai-sdk",
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

        if not self.api_key:
            return PlannerResult(
                actions=[],
                raw_output="No API key provided - set ZAI_API_KEY environment variable",
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

        # Build prompt
        prompt = self._build_prompt(context)

        # Log input
        self._log_planner_input(context)

        # Call GLM-4.7
        try:
            messages = []
            if system_prompt or self._get_default_system_prompt():
                messages.append({
                    "role": "system",
                    "content": system_prompt or self._get_default_system_prompt()
                })
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            raw_output = response.choices[0].message.content

            # Parse actions
            actions = self._parse_actions(raw_output)

            # Create result
            result = PlannerResult(
                actions=actions,
                raw_output=raw_output,
                timestamp=datetime.utcnow().isoformat() + "Z",
                model_used=self.model,
                tokens_used={
                    "input": response.usage.prompt_tokens if hasattr(response, "usage") else 0,
                    "output": response.usage.completion_tokens if hasattr(response, "usage") else 0,
                },
            )

            # Log output
            self._log_planner_output(result)

            return result

        except Exception as e:
            # Log error and return empty result
            error_msg = f"Error calling GLM-4.7: {e}"

            result = PlannerResult(
                actions=[],
                raw_output=error_msg,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

            self._log_planner_output(result)

            return result

    def _build_prompt(self, context: PlannerContext) -> str:
        """Build prompt from context.

        Args:
            context: Planner context.

        Returns:
            Prompt string.
        """
        from autolab.planner.prompts import get_context_prompt

        context_dict = self._context_to_dict(context)

        prompt_parts = [
            get_context_prompt(context_dict),
            "",
            "Based on this context, propose next actions. Return only JSON.",
            "",
            "Use this schema:",
            self._get_action_schema(),
        ]

        return "\n".join(prompt_parts)

    def _context_to_dict(self, context: PlannerContext) -> dict[str, Any]:
        """Convert PlannerContext to dictionary.

        Args:
            context: Planner context.

        Returns:
            Dictionary representation.
        """
        return {
            "goal": context.research_goal.model_dump(),
            "recent_history": context.recent_history,
            "best_results": context.best_results,
            "active_hypotheses": [h.model_dump() for h in context.active_hypotheses],
            "queue": context.queue_summary.model_dump(),
            "failures": context.failure_summary.recent_failure_types,
            "available_resources": context.available_resources,
            "policies": context.policy_constraints,
        }

    def _parse_actions(self, raw_output: str) -> list[PlannerAction]:
        """Parse actions from raw output.

        Args:
            raw_output: Raw JSON string from planner.

        Returns:
            List of PlannerAction objects.
        """
        # Extract JSON from output
        json_str = self._extract_json(raw_output)

        if not json_str:
            return []

        try:
            data = json.loads(json_str)

            if "actions" not in data:
                return []

            actions = []
            for action_data in data["actions"]:
                try:
                    action = PlannerAction(**action_data)
                    actions.append(action)
                except Exception:
                    # Skip invalid actions
                    continue

            return actions
        except json.JSONDecodeError:
            return []

    def _extract_json(self, text: str) -> str | None:
        """Extract JSON from text.

        Args:
            text: Text containing JSON.

        Returns:
            JSON string or None.
        """
        import re

        # Try to find JSON object
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return match.group(0)

        return None

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt.

        Returns:
            System prompt string.
        """
        from autolab.planner.prompts import PLANNER_SYSTEM_PROMPT

        return PLANNER_SYSTEM_PROMPT

    def _get_action_schema(self) -> str:
        """Get action schema.

        Returns:
            Schema string.
        """
        from autolab.planner.prompts import get_action_schema

        return get_action_schema()

    def _log_planner_input(self, context: PlannerContext) -> None:
        """Log planner input to file.

        Args:
            context: Planner context.
        """
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        cycle = context.cycle_info.get("cycle_count", 0)

        filename = self.raw_output_dir / f"{timestamp}_cycle_{cycle:04d}_input.json"

        with open(filename, "w") as f:
            json.dump(self._context_to_dict(context), f, indent=2)

    def _log_planner_output(self, result: PlannerResult) -> None:
        """Log planner output to file.

        Args:
            result: Planner result.
        """
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        # Extract cycle from raw output if possible, or use timestamp
        filename = self.raw_output_dir / f"{timestamp}_output.json"

        with open(filename, "w") as f:
            output_data = {
                "actions": [a.model_dump() for a in result.actions],
                "raw_output": result.raw_output,
                "timestamp": result.timestamp,
                "model_used": result.model_used,
                "tokens_used": result.tokens_used,
            }
            json.dump(output_data, f, indent=2)


from pydantic import BaseModel, Field
