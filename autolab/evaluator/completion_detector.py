"""Completion detector for detecting when experiments finish."""

import re
from pathlib import Path
from typing import Any


class CompletionResult(BaseModel):
    """Result of completion detection."""

    is_complete: bool = Field(..., description="Whether experiment completed")
    completion_reason: str = Field(..., description="Reason for completion status")
    success: bool = Field(..., description="Whether completed successfully")
    exit_code: int | None = Field(None, description="Exit code if available")
    metrics: dict[str, float | int | str] = Field(..., description="Extracted metrics")
    completion_time: str = Field(..., description="ISO timestamp of detection")


class CompletionDetector:
    """Detector for experiment completion."""

    def __init__(self) -> None:
        """Initialize completion detector."""
        self.success_indicators = [
            r"training completed",
            r"job finished",
            r"experiment finished",
            r"successfully completed",
            r"done\.",
            r"all experiments completed",
            r"evaluation finished",
            r"final.*accuracy",
            r"test.*accuracy",
        ]

        self.failure_indicators = {
            "oom": [
                r"out of memory",
                r"cuda out of memory",
                r"memory error",
                r"memory allocation failed",
            ],
            "timeout": [
                r"timeout",
                r"timed out",
                r"time limit exceeded",
            ],
            "syntax_error": [
                r"syntaxerror",
                r"invalid syntax",
                r"indentationerror",
            ],
            "import_error": [
                r"importerror",
                r"module not found",
                r"no module named",
            ],
            "nan_divergence": [
                r"nan loss",
                r"nan accuracy",
                r"divergence detected",
                r"gradient became nan",
            ],
            "dataset_missing": [
                r"file not found",
                r"no such file",
                r"dataset not found",
                r"path does not exist",
            ],
            "runtime_exception": [
                r"runtimeerror",
                r"exception:",
                r"traceback",
            ],
        }

    def detect_completion(
        self,
        experiment_id: str,
        log_path: str,
        process_running: bool,
        exit_code: int | None = None,
    ) -> CompletionResult:
        """Detect if an experiment has completed.

        Args:
            experiment_id: Experiment ID.
            log_path: Path to log file.
            process_running: Whether process is still running.
            exit_code: Exit code if available.

        Returns:
            CompletionResult object.
        """
        from datetime import datetime

        log_content = self._read_log(log_path)

        # Extract metrics
        metrics = self._extract_metrics(log_content)

        if process_running:
            # Still running
            return CompletionResult(
                is_complete=False,
                completion_reason="Process still running",
                success=False,
                exit_code=None,
                metrics=metrics,
                completion_time=datetime.utcnow().isoformat() + "Z",
            )

        # Process stopped - determine if completed successfully
        success = False
        reason = "Process stopped"

        if exit_code == 0:
            success = True
            reason = "Exited successfully"
        elif exit_code is not None:
            reason = f"Exited with code {exit_code}"
        else:
            # No exit code - check log for indicators
            if self._has_success_indicators(log_content):
                success = True
                reason = "Success indicators found in log"
            else:
                failure_type = self._detect_failure_type(log_content)
                if failure_type:
                    reason = f"Detected failure: {failure_type}"

        return CompletionResult(
            is_complete=True,
            completion_reason=reason,
            success=success,
            exit_code=exit_code,
            metrics=metrics,
            completion_time=datetime.utcnow().isoformat() + "Z",
        )

    def detect_from_result_file(
        self,
        result_path: str,
    ) -> CompletionResult:
        """Detect completion from a results file.

        Args:
            result_path: Path to results file (JSON).

        Returns:
            CompletionResult object.
        """
        from datetime import datetime

        path = Path(result_path)

        if not path.exists():
            return CompletionResult(
                is_complete=False,
                completion_reason="Result file not found",
                success=False,
                exit_code=None,
                metrics={},
                completion_time=datetime.utcnow().isoformat() + "Z",
            )

        try:
            import json

            with open(path) as f:
                data = json.load(f)

            # Extract metrics
            metrics = {}
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    metrics[key] = value

            # Assume success if file exists
            return CompletionResult(
                is_complete=True,
                completion_reason="Result file found",
                success=True,
                exit_code=0,
                metrics=metrics,
                completion_time=datetime.utcnow().isoformat() + "Z",
            )
        except Exception as e:
            return CompletionResult(
                is_complete=False,
                completion_reason=f"Error reading result file: {e}",
                success=False,
                exit_code=None,
                metrics={},
                completion_time=datetime.utcnow().isoformat() + "Z",
            )

    def _read_log(self, log_path: str) -> str:
        """Read log file content.

        Args:
            log_path: Path to log file.

        Returns:
            Log content string.
        """
        path = Path(log_path)
        if not path.exists():
            return ""

        try:
            with open(path, "r", errors="replace") as f:
                return f.read()
        except Exception:
            return ""

    def _has_success_indicators(self, content: str) -> bool:
        """Check if content has success indicators.

        Args:
            content: Log content.

        Returns:
            True if success indicators found.
        """
        content_lower = content.lower()
        for indicator in self.success_indicators:
            if re.search(indicator, content_lower):
                return True
        return False

    def _detect_failure_type(self, content: str) -> str | None:
        """Detect failure type from content.

        Args:
            content: Log content.

        Returns:
            Failure type string or None.
        """
        content_lower = content.lower()

        for failure_type, indicators in self.failure_indicators.items():
            for indicator in indicators:
                if re.search(indicator, content_lower):
                    return failure_type

        return None

    def _extract_metrics(self, content: str) -> dict[str, float | int | str]:
        """Extract metrics from log content.

        Args:
            content: Log content.

        Returns:
            Dictionary of metrics.
        """
        metrics = {}

        # Common metric patterns
        patterns = {
            "train_loss": r"train[_\s]loss[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "val_loss": r"val(?:idation)?[_\s]loss[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "test_loss": r"test[_\s]loss[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "train_acc": r"train[_\s]acc(?:uracy)?[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "val_acc": r"val(?:idation)?[_\s]acc(?:uracy)?[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "test_acc": r"test[_\s]acc(?:uracy)?[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "accuracy": r"accuracy[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "f1": r"f1[_\s]score[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "precision": r"precision[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "recall": r"recall[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "learning_rate": r"learning[_\s]rate[:\s]+([0-9]+(?:\.[0-9]+(?:e[+-]?[0-9]+)?)?)",
        }

        for metric_name, pattern in patterns.items():
            # Find all matches and take the last one
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                value_str = matches[-1].group(1)
                try:
                    if "." in value_str or "e" in value_str.lower():
                        metrics[metric_name] = float(value_str)
                    else:
                        metrics[metric_name] = int(value_str)
                except ValueError:
                    metrics[metric_name] = value_str

        return metrics

    def check_timeout(
        self,
        start_time: str,
        max_runtime_minutes: int | None = None,
    ) -> bool:
        """Check if experiment has exceeded timeout.

        Args:
            start_time: ISO timestamp of start time.
            max_runtime_minutes: Maximum runtime in minutes.

        Returns:
            True if timeout exceeded.
        """
        if max_runtime_minutes is None:
            return False

        from datetime import datetime

        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            elapsed = (datetime.utcnow() - start_dt).total_seconds()
            return elapsed > max_runtime_minutes * 60
        except Exception:
            return False

    def get_progress_estimate(
        self,
        log_path: str,
    ) -> dict[str, Any]:
        """Get progress estimate from log.

        Args:
            log_path: Path to log file.

        Returns:
            Dictionary with progress info.
        """
        content = self._read_log(log_path)

        # Extract epoch/step info
        epoch_matches = re.findall(r"epoch[:\s]+(\d+)", content, re.IGNORECASE)
        step_matches = re.findall(r"step[:\s]+(\d+)", content, re.IGNORECASE)

        progress = {
            "has_progress": False,
            "current_epoch": int(epoch_matches[-1]) if epoch_matches else None,
            "max_epoch": None,
            "current_step": int(step_matches[-1]) if step_matches else None,
            "max_step": None,
            "progress_percent": None,
        }

        if epoch_matches:
            progress["has_progress"] = True
            progress["max_epoch"] = max(map(int, epoch_matches))

        if step_matches:
            progress["has_progress"] = True
            progress["max_step"] = max(map(int, step_matches))

        return progress


from pydantic import BaseModel, Field
