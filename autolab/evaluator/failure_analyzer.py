"""Failure analyzer for analyzing experiment failures."""

import re
from collections import Counter, defaultdict
from typing import Any

from autolab.schemas.result import Result
from autolab.schemas.state import FailureSummary


class FailurePattern(BaseModel):
    """Represents a recurring failure pattern."""

    failure_type: str = Field(..., description="Type of failure")
    count: int = Field(..., description="Number of occurrences")
    common_pattern: str = Field(..., description="Common pattern description")
    affected_experiments: list[str] = Field(..., description="Experiment IDs affected")
    suggested_fix: str = Field(..., description="Suggested fix")


class FailureAnalyzer:
    """Analyzer for experiment failures."""

    def __init__(self) -> None:
        """Initialize failure analyzer."""
        self.failure_taxonomy = {
            "oom": ["out of memory", "cuda out of memory", "memory error", "memory allocation failed"],
            "timeout": ["timeout", "timed out", "time limit exceeded"],
            "syntax_error": ["syntaxerror", "invalid syntax", "indentationerror"],
            "import_error": ["importerror", "module not found", "no module named"],
            "nan_divergence": ["nan loss", "nan accuracy", "divergence detected", "gradient became nan"],
            "dataset_missing": ["file not found", "no such file", "dataset not found", "path does not exist"],
            "bad_config": ["config error", "configuration error", "invalid config"],
            "runtime_exception": ["runtimeerror", "exception:", "error:"],
            "ssh_failure": ["ssh connection", "connection refused", "authentication failed"],
            "worker_unreachable": ["host unreachable", "connection timed out", "network unreachable"],
        }

    def classify_failure(self, log_content: str, stderr: str | None = None) -> str | None:
        """Classify failure type from logs.

        Args:
            log_content: Log content.
            stderr: Standard error content.

        Returns:
            Failure type string or None.
        """
        combined_content = log_content.lower()
        if stderr:
            combined_content += " " + stderr.lower()

        for failure_type, indicators in self.failure_taxonomy.items():
            for indicator in indicators:
                if indicator.lower() in combined_content:
                    return failure_type

        return "unknown"

    def extract_failure_details(
        self,
        result: Result,
        log_content: str,
    ) -> dict[str, Any]:
        """Extract detailed failure information.

        Args:
            result: Result object.
            log_content: Log content.

        Returns:
            Dictionary with failure details.
        """
        details = {
            "failure_type": result.failure_type,
            "failure_reason": result.failure_reason,
        }

        if not result.success:
            # Extract error message
            error_match = re.search(r"(?:error|exception):?\s*(.+?)(?:\n|$)", log_content, re.IGNORECASE)
            if error_match:
                details["error_message"] = error_match.group(1).strip()

            # Extract stack trace
            trace_match = re.search(r"traceback \(most recent call last\):.*?(?=error|exception|$)", log_content, re.DOTALL | re.IGNORECASE)
            if trace_match:
                details["stack_trace"] = trace_match.group(0).strip()

            # Extract file and line number
            file_match = re.search(r'file "(.+?)", line (\d+)', log_content, re.IGNORECASE)
            if file_match:
                details["error_file"] = file_match.group(1)
                details["error_line"] = int(file_match.group(2))

            # OOM specific
            if result.failure_type == "oom":
                memory_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mb|gb|mi|gi)", log_content, re.IGNORECASE)
                if memory_match:
                    details["memory_amount"] = memory_match.group(1)

        return details

    def analyze_recurring_failures(
        self,
        results: dict[str, Result],
        experiments: dict[str, Any],
    ) -> list[FailurePattern]:
        """Analyze recurring failure patterns.

        Args:
            results: Dictionary of results.
            experiments: Dictionary of experiments.

        Returns:
            List of FailurePattern objects.
        """
        # Group failures by type
        failures_by_type: dict[str, list[str]] = defaultdict(list)

        for exp_id, result in results.items():
            if not result.success and result.failure_type:
                failures_by_type[result.failure_type].append(exp_id)

        # Analyze patterns
        patterns = []
        for failure_type, exp_ids in failures_by_type.items():
            if len(exp_ids) < 2:
                continue

            # Get common pattern
            common_pattern = self._get_common_pattern(exp_ids, experiments)

            # Get suggested fix
            suggested_fix = self._get_suggested_fix(failure_type, exp_ids, experiments)

            patterns.append(
                FailurePattern(
                    failure_type=failure_type,
                    count=len(exp_ids),
                    common_pattern=common_pattern,
                    affected_experiments=exp_ids,
                    suggested_fix=suggested_fix,
                )
            )

        # Sort by count
        patterns.sort(key=lambda p: p.count, reverse=True)

        return patterns

    def get_failure_summary(
        self,
        results: dict[str, Result],
    ) -> FailureSummary:
        """Get summary of all failures.

        Args:
            results: Dictionary of results.

        Returns:
            FailureSummary object.
        """
        failed_results = [r for r in results.values() if not r.success]

        # Count by type
        failure_types = Counter()
        for r in failed_results:
            if r.failure_type:
                failure_types[r.failure_type] += 1

        # Analyze recurring patterns
        # Note: We'd need experiments dict for full analysis
        recurring = []

        return FailureSummary(
            total_failures=len(failed_results),
            recurring_failures=[p.model_dump() for p in recurring],
            recent_failure_types=list(failure_types.keys()),
        )

    def should_retry(self, result: Result, retry_count: int, max_retries: int = 1) -> bool:
        """Determine if an experiment should be retried.

        Args:
            result: Result object.
            retry_count: Current retry count.
            max_retries: Maximum retries allowed.

        Returns:
            True if should retry.
        """
        if retry_count >= max_retries:
            return False

        # Don't retry on certain failure types
        no_retry_types = {"syntax_error", "import_error", "bad_config"}
        if result.failure_type in no_retry_types:
            return False

        # Retry on transient failures
        transient_types = {"oom", "timeout", "ssh_failure", "worker_unreachable"}
        if result.failure_type in transient_types:
            return True

        # Default: retry once on unknown failures
        if result.failure_type == "unknown" and retry_count == 0:
            return True

        return False

    def suggest_retry_config(
        self,
        experiment: dict[str, Any],
        failure_type: str,
    ) -> dict[str, Any]:
        """Suggest configuration changes for retry.

        Args:
            experiment: Experiment dictionary.
            failure_type: Type of failure.

        Returns:
            Dictionary with suggested config changes.
        """
        suggestions = {}

        resource_request = experiment.get("resource_request", {})

        if failure_type == "oom":
            # Reduce batch size
            current_batch = resource_request.get("batch_size", 64)
            suggestions["batch_size"] = current_batch // 2

            # Maybe reduce gradient accumulation
            if "gradient_accumulation_steps" in resource_request:
                current_grad = resource_request["gradient_accumulation_steps"]
                suggestions["gradient_accumulation_steps"] = current_grad * 2

        elif failure_type == "timeout":
            # Reduce max runtime
            current_runtime = experiment.get("max_runtime_minutes", 60)
            suggestions["max_runtime_minutes"] = current_runtime * 1.5

        elif failure_type == "nan_divergence":
            # Reduce learning rate
            config_snapshot = experiment.get("config_snapshot", {})
            if "train" in config_snapshot and "lr" in config_snapshot["train"]:
                current_lr = config_snapshot["train"]["lr"]
                suggestions["lr"] = current_lr * 0.1

        return suggestions

    def _get_common_pattern(
        self,
        exp_ids: list[str],
        experiments: dict[str, Any],
    ) -> str:
        """Get common pattern description.

        Args:
            exp_ids: Experiment IDs.
            experiments: Experiments dictionary.

        Returns:
            Pattern description string.
        """
        # This would analyze commonalities between failed experiments
        # For now, return a simple description
        if len(exp_ids) == 1:
            return f"Single occurrence"

        # Check if all have same family
        families = set()
        for exp_id in exp_ids:
            if exp_id in experiments:
                families.add(experiments[exp_id].get("family"))

        if len(families) == 1:
            family = families.pop()
            return f"Recurring issue in {family} experiments"

        return f"Pattern affecting {len(exp_ids)} experiments"

    def _get_suggested_fix(
        self,
        failure_type: str,
        exp_ids: list[str],
        experiments: dict[str, Any],
    ) -> str:
        """Get suggested fix for failure type.

        Args:
            failure_type: Type of failure.
            exp_ids: Affected experiment IDs.
            experiments: Experiments dictionary.

        Returns:
            Suggested fix string.
        """
        fixes = {
            "oom": "Reduce batch size or model size, use gradient accumulation, or use GPU with more memory",
            "timeout": "Increase timeout limit or optimize code for faster execution",
            "syntax_error": "Fix syntax errors in code - these should be caught before running",
            "import_error": "Install missing dependencies or fix import paths",
            "nan_divergence": "Reduce learning rate, check data normalization, add gradient clipping",
            "dataset_missing": "Verify dataset path and ensure files exist",
            "bad_config": "Fix configuration errors",
            "runtime_exception": "Debug the runtime error - check logs for details",
            "ssh_failure": "Check SSH connection and credentials",
            "worker_unreachable": "Check network connectivity and worker status",
            "unknown": "Review logs to determine root cause",
        }

        return fixes.get(failure_type, "Review logs for details")


from pydantic import BaseModel, Field
