"""Context builder for preparing planner context."""

from datetime import datetime
from typing import Any

from autolab.schemas.experiment import Experiment
from autolab.schemas.hypothesis import Hypothesis
from autolab.schemas.result import Result
from autolab.schemas.state import (
    FailureSummary,
    GlobalState,
    QueueSummary,
    ResearchGoal,
)


class PlannerContext(BaseModel):
    """Context provided to the planner."""

    research_goal: ResearchGoal = Field(..., description="Current research goal")
    recent_history: list[dict] = Field(..., description="Recent experiment history")
    best_results: dict[str, Any] = Field(..., description="Best results per family/metric")
    active_hypotheses: list[Hypothesis] = Field(..., description="Active hypotheses")
    queue_summary: QueueSummary = Field(..., description="Queue status")
    failure_summary: FailureSummary = Field(..., description="Recent failure patterns")
    policy_constraints: dict[str, Any] = Field(..., description="Policy constraints")
    worker_status: dict[str, Any] = Field(..., description="Worker availability")
    available_resources: dict[str, Any] = Field(..., description="Available resources")
    cycle_info: dict[str, Any] = Field(..., description="Current cycle information")

    timestamp: str = Field(..., description="ISO timestamp of context creation")


class ContextBuilder:
    """Builder for creating planner context."""

    def __init__(
        self,
        workspace_path: str = "./autolab_workspace",
        max_history_items: int = 20,
    ) -> None:
        """Initialize context builder.

        Args:
            workspace_path: Path to workspace.
            max_history_items: Maximum number of history items to include.
        """
        self.workspace_path = workspace_path
        self.max_history_items = max_history_items

    def build(
        self,
        global_state: GlobalState,
        experiments: dict[str, Experiment],
        results: dict[str, Result],
        hypotheses: dict[str, Hypothesis],
        queue_summary: QueueSummary,
        failure_summary: FailureSummary,
        policy_constraints: dict[str, Any],
        worker_status: dict[str, Any],
        available_resources: dict[str, Any],
        cycle_count: int,
    ) -> PlannerContext:
        """Build planner context.

        Args:
            global_state: Global state.
            experiments: All experiments.
            results: All results.
            hypotheses: All hypotheses.
            queue_summary: Queue summary.
            failure_summary: Failure summary.
            policy_constraints: Policy constraints.
            worker_status: Worker status.
            available_resources: Available resources.
            cycle_count: Current cycle count.

        Returns:
            PlannerContext object.
        """
        # Build recent history
        recent_history = self._build_recent_history(
            global_state.recent_history,
            experiments,
            results,
        )

        # Build best results
        best_results = self._build_best_results(results, experiments)

        # Filter active hypotheses
        active_hypotheses = [
            h for h in hypotheses.values()
            if h.status == "active"
        ]

        return PlannerContext(
            research_goal=global_state.goal,
            recent_history=recent_history,
            best_results=best_results,
            active_hypotheses=active_hypotheses,
            queue_summary=queue_summary,
            failure_summary=failure_summary,
            policy_constraints=policy_constraints,
            worker_status=worker_status,
            available_resources=available_resources,
            cycle_info={
                "cycle_count": cycle_count,
                "total_experiments": global_state.lab_status.total_experiments,
                "completed_experiments": global_state.lab_status.completed_experiments,
                "failed_experiments": global_state.lab_status.failed_experiments,
            },
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    def _build_recent_history(
        self,
        experiment_ids: list[str],
        experiments: dict[str, Experiment],
        results: dict[str, Result],
    ) -> list[dict]:
        """Build recent history from experiment IDs.

        Args:
            experiment_ids: List of experiment IDs (in order).
            experiments: All experiments.
            results: All results.

        Returns:
            List of history entries.
        """
        history = []

        # Take most recent N
        recent_ids = experiment_ids[-self.max_history_items:]

        for exp_id in recent_ids:
            exp = experiments.get(exp_id)
            if not exp:
                continue

            entry = {
                "experiment_id": exp.id,
                "title": exp.title,
                "status": exp.status,
                "family": exp.family,
                "created_at": exp.created_at,
            }

            # Add result if available
            if exp_id in results:
                result = results[exp_id]
                entry["success"] = result.success
                entry["metrics"] = result.metrics
                entry["runtime_seconds"] = result.runtime_seconds

                if not result.success:
                    entry["failure_type"] = result.failure_type

            history.append(entry)

        return history

    def _build_best_results(
        self,
        results: dict[str, Result],
        experiments: dict[str, Experiment],
    ) -> dict[str, Any]:
        """Build best results summary.

        Args:
            results: All results.
            experiments: All experiments.

        Returns:
            Dictionary with best results.
        """
        best_results = {}

        # Group by family
        by_family: dict[str, list[tuple[str, Result]]] = {}
        for exp_id, result in results.items():
            if not result.success:
                continue

            exp = experiments.get(exp_id)
            if not exp or not exp.family:
                continue

            if exp.family not in by_family:
                by_family[exp.family] = []

            by_family[exp.family].append((exp_id, result))

        # Find best in each family by primary metric
        for family, family_results in by_family.items():
            # Use val_acc or first metric
            for exp_id, result in family_results:
                metrics = result.metrics

                # Find primary metric
                primary_metric = None
                for metric in ["val_acc", "test_acc", "accuracy", "f1", "val_loss"]:
                    if metric in metrics:
                        primary_metric = metric
                        break

                if primary_metric is None and metrics:
                    primary_metric = list(metrics.keys())[0]

                if primary_metric is None:
                    continue

                # Check if this is the best
                if family not in best_results:
                    best_results[family] = {
                        "experiment_id": exp_id,
                        "metric_name": primary_metric,
                        "metric_value": float(metrics[primary_metric]),
                    }
                else:
                    current_best = best_results[family]["metric_value"]
                    new_value = float(metrics[primary_metric])

                    # Higher is better for accuracy
                    if primary_metric in ["val_acc", "test_acc", "accuracy", "f1"]:
                        if new_value > current_best:
                            best_results[family] = {
                                "experiment_id": exp_id,
                                "metric_name": primary_metric,
                                "metric_value": new_value,
                            }
                    # Lower is better for loss
                    elif primary_metric in ["val_loss", "test_loss"]:
                        if new_value < current_best:
                            best_results[family] = {
                                "experiment_id": exp_id,
                                "metric_name": primary_metric,
                                "metric_value": new_value,
                            }

        return best_results

    def build_for_action(
        self,
        action_type: str,
        context: PlannerContext,
        experiment_id: str | None = None,
    ) -> dict[str, Any]:
        """Build context for a specific action.

        Args:
            action_type: Type of action being planned.
            context: Full planner context.
            experiment_id: Optional experiment ID for action.

        Returns:
            Simplified context for action.
        """
        action_context = {
            "goal": context.research_goal.model_dump(),
            "policies": context.policy_constraints,
        }

        if action_type in ["patch_config", "patch_code"]:
            if experiment_id:
                exp = next((h for h in context.recent_history if h["experiment_id"] == experiment_id), None)
                if exp:
                    action_context["experiment"] = exp

        elif action_type in ["create_experiment", "create_hypothesis"]:
            action_context["best_results"] = context.best_results
            action_context["failures"] = context.failure_summary.recent_failure_types

        elif action_type == "generate_report":
            action_context["cycle_info"] = context.cycle_info
            action_context["queue"] = context.queue_summary.model_dump()

        return action_context


from pydantic import BaseModel, Field
