"""Main loop for the autonomous lab controller."""

import time
from datetime import datetime
from typing import Any

from autolab.controller.action_validator import ActionValidator
from autolab.controller.heartbeat import Heartbeat
from autolab.controller.policies import PolicyManager
from autolab.evaluator.completion_detector import CompletionDetector, CompletionResult
from autolab.evaluator.failure_analyzer import FailureAnalyzer
from autolab.evaluator.metric_parser import MetricParser
from autolab.executor.job_runner import JobRunner
from autolab.executor.worker_registry import WorkerRegistry
from autolab.planner.context_builder import ContextBuilder, PlannerContext
from autolab.planner.openclaw_bridge import OpenClawBridge
from autolab.schemas.action import PlannerAction
from autolab.schemas.experiment import Experiment
from autolab.schemas.result import Result
from autolab.storage.artifact_store import ArtifactStore
from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.git_snapshot import GitSnapshot
from autolab.storage.result_store import ResultStore
from autolab.storage.state_store import StateStore


class MainLoop:
    """Main control loop for autonomous lab."""

    def __init__(
        self,
        workspace_path: str = "./autolab_workspace",
        config_path: str = "./autolab/configs",
        loop_interval_seconds: float = 60.0,
        api_key: str | None = None,
    ) -> None:
        """Initialize main loop.

        Args:
            workspace_path: Path to workspace.
            config_path: Path to config directory.
            loop_interval_seconds: Interval between loop cycles.
            api_key: Anthropic API key for OpenClaw.
        """
        self.workspace_path = workspace_path
        self.loop_interval = loop_interval_seconds

        # Initialize components
        self.state_store = StateStore(workspace_path)
        self.experiment_store = ExperimentStore(workspace_path)
        self.result_store = ResultStore(workspace_path)
        self.artifact_store = ArtifactStore(workspace_path)
        self.worker_registry = WorkerRegistry(f"{config_path}/gpu.yaml")
        self.job_runner = JobRunner(self.worker_registry, workspace_path)

        # Initialize analyzers
        self.metric_parser = MetricParser()
        self.completion_detector = CompletionDetector()
        self.failure_analyzer = FailureAnalyzer()

        # Initialize planner
        self.context_builder = ContextBuilder(workspace_path)
        self.openclaw_bridge = OpenClawBridge(
            api_key=api_key,
            workspace_path=workspace_path,
        )

        # Initialize controller components
        self.policy_manager = PolicyManager(f"{config_path}/policies.yaml")
        self.action_validator = ActionValidator(workspace_path)
        self.heartbeat = Heartbeat(
            f"{workspace_path}/state/heartbeat.txt",
            interval_seconds=loop_interval_seconds,
        )

        # Track state for cycle
        self.cycle_count = 0
        self.experiments_created_this_cycle = 0
        self.hypotheses_created_this_cycle = 0

    def run(self) -> None:
        """Run the main loop."""
        print(f"Starting autonomous lab controller (PID: {self.heartbeat.pid})")
        print(f"Workspace: {self.workspace_path}")
        print(f"Loop interval: {self.loop_interval}s")

        try:
            while True:
                self.run_cycle()

                # Sleep until next cycle
                time.sleep(self.loop_interval)

        except KeyboardInterrupt:
            print("\nShutting down controller...")
            self.shutdown()

    def run_cycle(self) -> None:
        """Run a single cycle."""
        self.cycle_count += 1
        cycle_start = time.time()

        print(f"\n=== Cycle {self.cycle_count} === {datetime.utcnow().isoformat()}")

        # Reset per-cycle counters
        self.experiments_created_this_cycle = 0
        self.hypotheses_created_this_cycle = 0

        try:
            # Step 1: Load state
            global_state = self.state_store.load_global_state()
            experiments = self.experiment_store.load_all()
            results = self.result_store.load_all()
            hypotheses = self.state_store.load_hypotheses()

            print(f"Loaded state: {len(experiments)} experiments, {len(results)} results")

            # Step 2: Update worker heartbeats
            offline_workers = self.worker_registry.check_heartbeats()
            if offline_workers:
                print(f"Workers went offline: {offline_workers}")

            # Step 3: Check running experiments
            running_experiments = self.experiment_store.get_running_experiments()
            completed_results = self._check_running_jobs(running_experiments, experiments)
            print(f"Completed {len(completed_results)} jobs")

            # Step 4: Update dependency satisfaction
            ready_count = self.experiment_store.update_dependencies_satisfied()
            if ready_count:
                print(f"Updated {len(ready_count)} experiments to ready")

            # Step 5: Update global state
            self._update_global_state(global_state, experiments, results, completed_results)

            # Step 6: Dispatch ready experiments
            dispatched = self._dispatch_ready_jobs(experiments)
            print(f"Dispatched {len(dispatched)} jobs")

            # Step 7: Build planner context
            context = self._build_planner_context(
                global_state,
                experiments,
                results,
                hypotheses,
            )

            # Step 8: Get planner actions
            planner_result = self.openclaw_bridge.propose_actions(context)
            print(f"Planner proposed {len(planner_result.actions)} actions")

            # Step 9: Validate actions
            valid_actions, errors = self.action_validator.validate_all(
                planner_result.actions,
                self.policy_manager.get_all(),
                experiments,
            )

            if errors:
                print(f"Rejected {len(errors)} actions due to validation errors")

            # Step 10: Apply valid actions
            applied = self._apply_actions(valid_actions, experiments, hypotheses)
            print(f"Applied {len(applied)} actions")

            # Step 11: Save state
            self.experiment_store.save_all(experiments)
            self.state_store.save_global_state(global_state)
            self.state_store.save_hypotheses(hypotheses)
            self.result_store.save_all(results)

            # Step 12: Update heartbeat
            self.heartbeat.update_cycle_count(self.cycle_count)

            cycle_duration = time.time() - cycle_start
            print(f"Cycle {self.cycle_count} completed in {cycle_duration:.1f}s")

        except Exception as e:
            print(f"Error in cycle {self.cycle_count}: {e}")
            import traceback

            traceback.print_exc()

    def _check_running_jobs(
        self,
        running_experiments: dict[str, Experiment],
        all_experiments: dict[str, Experiment],
    ) -> list[Result]:
        """Check status of running experiments.

        Args:
            running_experiments: Dictionary of running experiments.
            all_experiments: All experiments.

        Returns:
            List of newly completed results.
        """
        completed_results = []

        for exp_id, experiment in running_experiments.items():
            if not experiment.worker_name or not experiment.pid:
                continue

            # Get log path
            log_path = self.artifact_store._get_log_path(exp_id)

            # Check if process is still running
            status = self.job_runner.check_experiment_status(experiment)

            # Detect completion
            completion = self.completion_detector.detect_completion(
                experiment_id=exp_id,
                log_path=log_path,
                process_running=status.running,
            )

            if completion.is_complete:
                # Create result
                result = self._create_result(
                    experiment,
                    completion,
                    status,
                    log_path,
                )

                completed_results.append(result)

                # Update experiment status
                if completion.success:
                    experiment.status = "completed"
                else:
                    experiment.status = "failed"

                experiment.finished_at = completion.completion_time

                # Save result
                self.result_store.save(result)

                # Update worker job count
                self.worker_registry.decrement_job_count(experiment.worker_name)

        return completed_results

    def _create_result(
        self,
        experiment: Experiment,
        completion: CompletionResult,
        process_status: Any,
        log_path: str,
    ) -> Result:
        """Create a result from experiment completion.

        Args:
            experiment: Experiment.
            completion: Completion detection result.
            process_status: Process status.
            log_path: Log file path.

        Returns:
            Result object.
        """
        from datetime import datetime

        # Parse metrics from log
        metrics = self.metric_parser.parse_from_log(log_path)
        metrics.update(completion.metrics)

        # Determine failure type
        failure_type = None
        failure_reason = None

        if not completion.success:
            log_content = self._read_log_content(log_path)
            failure_type = completion.completion_reason
            failure_reason = self.failure_analyzer.extract_failure_details(
                Result(
                    experiment_id=experiment.id,
                    success=False,
                    metrics=metrics,
                    summary="",
                    log_path=log_path,
                    parsed_at=datetime.utcnow().isoformat() + "Z",
                ),
                log_content,
            ).get("error_message")

        return Result(
            experiment_id=experiment.id,
            success=completion.success,
            metrics=metrics,
            summary=self._generate_summary(completion, metrics),
            log_path=log_path,
            runtime_seconds=process_status.uptime_seconds,
            gpu_id=experiment.gpu_id,
            host=experiment.worker_name,
            exit_code=completion.exit_code,
            failure_type=failure_type,
            failure_reason=failure_reason,
            artifact_paths=self._extract_artifacts(experiment.id),
            parsed_at=datetime.utcnow().isoformat() + "Z",
        )

    def _dispatch_ready_jobs(self, experiments: dict[str, Experiment]) -> list[JobLaunchResult]:
        """Dispatch ready experiments.

        Args:
            experiments: All experiments.

        Returns:
            List of launch results.
        """
        ready_experiments = self.experiment_store.get_ready_experiments()

        # Sort by priority
        sorted_ready = sorted(
            ready_experiments.values(),
            key=lambda e: e.priority,
            reverse=True,
        )

        launched = []

        for experiment in sorted_ready:
            # Check if we can schedule
            decision = self.job_runner._select_worker(experiment)
            if not decision:
                continue

            # Launch job
            result = self.job_runner.launch_experiment(experiment)

            if result.success:
                # Update experiment status
                experiments[experiment.id].status = "running"
                experiments[experiment.id].started_at = result.launch_time
                experiments[experiment.id].worker_name = result.worker_name
                experiments[experiment.id].gpu_id = result.gpu_id
                experiments[experiment.id].pid = result.pid

                launched.append(result)
            else:
                print(f"Failed to launch {experiment.id}: {result.error_message}")

        return launched

    def _build_planner_context(
        self,
        global_state: Any,
        experiments: dict[str, Experiment],
        results: dict[str, Result],
        hypotheses: dict[str, Any],
    ) -> PlannerContext:
        """Build planner context.

        Args:
            global_state: Global state.
            experiments: All experiments.
            results: All results.
            hypotheses: All hypotheses.

        Returns:
            Planner context.
        """
        queue_summary = self.state_store.get_queue_summary(experiments)
        failure_summary = self.state_store.get_failure_summary(results)

        best_results = {}
        for family, result in self.result_store.get_successful().items():
            pass  # TODO: implement best results logic

        return self.context_builder.build(
            global_state=global_state,
            experiments=experiments,
            results=results,
            hypotheses=hypotheses,
            queue_summary=queue_summary,
            failure_summary=failure_summary,
            policy_constraints=self.policy_manager.get_all(),
            worker_status=self.worker_registry.get_worker_summary(),
            available_resources=self.job_runner.scheduler.get_resource_summary(),
            cycle_count=self.cycle_count,
        )

    def _apply_actions(
        self,
        actions: list[PlannerAction],
        experiments: dict[str, Experiment],
        hypotheses: dict[str, Any],
    ) -> list[str]:
        """Apply validated planner actions.

        Args:
            actions: Valid actions to apply.
            experiments: All experiments.
            hypotheses: All hypotheses.

        Returns:
            List of applied action summaries.
        """
        applied = []

        for action in actions:
            try:
                summary = self._apply_single_action(action, experiments, hypotheses)
                if summary:
                    applied.append(summary)
            except Exception as e:
                print(f"Failed to apply action {action.action_type}: {e}")

        return applied

    def _apply_single_action(
        self,
        action: PlannerAction,
        experiments: dict[str, Experiment],
        hypotheses: dict[str, Any],
    ) -> str | None:
        """Apply a single action.

        Args:
            action: Action to apply.
            experiments: All experiments.
            hypotheses: All hypotheses.

        Returns:
            Summary string or None.
        """
        if action.action_type == "create_experiment":
            return self._handle_create_experiment(action, experiments)

        elif action.action_type == "create_hypothesis":
            return self._handle_create_hypothesis(action, hypotheses)

        # TODO: Implement other action handlers

        return None

    def _handle_create_experiment(
        self,
        action: PlannerAction,
        experiments: dict[str, Experiment],
    ) -> str:
        """Handle create_experiment action.

        Args:
            action: Action to apply.
            experiments: All experiments.

        Returns:
            Summary string.
        """
        from datetime import datetime

        payload = action.payload

        # Generate experiment ID
        exp_count = len(experiments) + 1
        exp_id = f"exp_{exp_count:04d}"

        # Get git snapshot
        git_snapshot = GitSnapshot(".").get_snapshot()

        # Create experiment
        experiment = Experiment(
            id=exp_id,
            hypothesis_id=None,
            title=payload["title"],
            description=payload["description"],
            objective=payload["objective"],
            family=payload.get("family"),
            parent_experiment_id=payload.get("parent_experiment_id"),
            baseline_experiment_id=payload.get("baseline_experiment_id"),
            status="pending",
            priority=payload.get("priority", 1.0),
            tags=payload.get("tags", []),
            dependencies=payload.get("dependencies", []),
            config_path=payload.get("config_path", "./config.yaml"),
            config_snapshot=payload.get("config_patch", {}),
            code_snapshot=git_snapshot,
            resource_request=payload.get("resource_request", {}),
            launch_command=payload.get("launch_command", []),
            working_dir=payload.get("working_dir", "."),
            dataset_info=payload.get("dataset_info", {}),
            planner_rationale=action.rationale,
            created_by="openclaw",
            max_runtime_minutes=payload.get("max_runtime_minutes"),
            retry_count=0,
            max_retries=1,
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        experiments[exp_id] = experiment
        self.experiments_created_this_cycle += 1

        return f"Created experiment: {exp_id} - {experiment.title}"

    def _handle_create_hypothesis(
        self,
        action: PlannerAction,
        hypotheses: dict[str, Any],
    ) -> str:
        """Handle create_hypothesis action.

        Args:
            action: Action to apply.
            hypotheses: All hypotheses.

        Returns:
            Summary string.
        """
        from datetime import datetime

        payload = action.payload

        # Generate hypothesis ID
        hyp_count = len(hypotheses) + 1
        hyp_id = f"hyp_{hyp_count:04d}"

        from autolab.schemas.hypothesis import Hypothesis

        hypothesis = Hypothesis(
            id=hyp_id,
            title=payload["title"],
            rationale=payload["rationale"],
            expected_effect=payload["expected_effect"],
            priority=payload.get("priority", 1.0),
            related_experiments=[],
            status="active",
            created_by="openclaw",
            created_at=datetime.utcnow().isoformat() + "Z",
            family=payload.get("family"),
            tags=payload.get("tags", []),
        )

        hypotheses[hyp_id] = hypothesis
        self.hypotheses_created_this_cycle += 1

        return f"Created hypothesis: {hyp_id} - {hypothesis.title}"

    def _update_global_state(
        self,
        global_state: Any,
        experiments: dict[str, Experiment],
        results: dict[str, Result],
        completed_results: list[Result],
    ) -> None:
        """Update global state with current information.

        Args:
            global_state: Global state to update.
            experiments: All experiments.
            results: All results.
            completed_results: Newly completed results.
        """
        # Update lab status
        global_state.lab_status.cycle_count = self.cycle_count
        global_state.lab_status.total_experiments = len(experiments)
        global_state.lab_status.completed_experiments = sum(
            1 for e in experiments.values() if e.status == "completed"
        )
        global_state.lab_status.failed_experiments = sum(
            1 for e in experiments.values() if e.status == "failed"
        )
        global_state.lab_status.running_experiments = sum(
            1 for e in experiments.values() if e.status == "running"
        )
        global_state.lab_status.last_cycle_time = datetime.utcnow().isoformat() + "Z"

        # Update recent history
        for result in completed_results:
            if result.experiment_id not in global_state.recent_history:
                global_state.recent_history.append(result.experiment_id)

            # Limit history size
            if len(global_state.recent_history) > 100:
                global_state.recent_history = global_state.recent_history[-100:]

        # Update timestamp
        global_state.updated_at = datetime.utcnow().isoformat() + "Z"

    def shutdown(self) -> None:
        """Shutdown controller cleanly."""
        print("Cleaning up...")

        # Clear heartbeat
        self.heartbeat.clear()

        # Cleanup job runner
        self.job_runner.cleanup()

        print("Shutdown complete.")

    def _read_log_content(self, log_path: str) -> str:
        """Read log file content.

        Args:
            log_path: Path to log file.

        Returns:
            Log content.
        """
        path = Path(log_path)
        if not path.exists():
            return ""

        try:
            with open(path, "r", errors="replace") as f:
                return f.read()
        except Exception:
            return ""

    def _generate_summary(
        self,
        completion: CompletionResult,
        metrics: dict,
    ) -> str:
        """Generate result summary.

        Args:
            completion: Completion result.
            metrics: Extracted metrics.

        Returns:
            Summary string.
        """
        parts = [completion.completion_reason]

        if metrics:
            top_metrics = list(metrics.items())[:3]
            metrics_str = ", ".join(f"{k}={v}" for k, v in top_metrics)
            parts.append(f"Metrics: {metrics_str}")

        return " | ".join(parts)

    def _extract_artifacts(self, experiment_id: str) -> list[str]:
        """Extract artifact paths.

        Args:
            experiment_id: Experiment ID.

        Returns:
            List of artifact paths.
        """
        # This would scan the artifacts directory
        return []
