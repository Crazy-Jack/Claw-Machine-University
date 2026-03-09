"""Metric parser for extracting metrics from experiment logs."""

import json
import re
from pathlib import Path
from typing import Any


class MetricParser:
    """Parser for extracting metrics from experiment logs."""

    def __init__(self, patterns: dict[str, str] | None = None) -> None:
        """Initialize metric parser.

        Args:
            patterns: Dictionary mapping metric names to regex patterns.
        """
        self.patterns = patterns or self._get_default_patterns()

    def parse_from_log(
        self,
        log_path: str,
    ) -> dict[str, float | int | str]:
        """Parse metrics from a log file.

        Args:
            log_path: Path to log file.

        Returns:
            Dictionary of extracted metrics.
        """
        log_content = self._read_log(log_path)
        return self.parse_from_content(log_content)

    def parse_from_content(
        self,
        content: str,
    ) -> dict[str, float | int | str]:
        """Parse metrics from log content.

        Args:
            content: Log content string.

        Returns:
            Dictionary of extracted metrics.
        """
        metrics = {}

        for metric_name, pattern in self.patterns.items():
            match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
            if match:
                value_str = match.group(1) if match.groups() else match.group(0)

                # Try to parse as number
                try:
                    if "." in value_str:
                        metrics[metric_name] = float(value_str)
                    else:
                        metrics[metric_name] = int(value_str)
                except ValueError:
                    metrics[metric_name] = value_str

        return metrics

    def parse_final_metrics(
        self,
        log_path: str,
    ) -> dict[str, float | int | str]:
        """Parse final metrics (last occurrence) from log.

        Args:
            log_path: Path to log file.

        Returns:
            Dictionary of final metrics.
        """
        log_content = self._read_log(log_path)
        metrics = {}

        for metric_name, pattern in self.patterns.items():
            # Find all matches and take the last one
            matches = list(re.finditer(pattern, log_content, re.MULTILINE | re.IGNORECASE))
            if matches:
                value_str = matches[-1].group(1) if matches[-1].groups() else matches[-1].group(0)

                try:
                    if "." in value_str:
                        metrics[metric_name] = float(value_str)
                    else:
                        metrics[metric_name] = int(value_str)
                except ValueError:
                    metrics[metric_name] = value_str

        return metrics

    def parse_from_json(
        self,
        json_path: str,
    ) -> dict[str, float | int | str]:
        """Parse metrics from a JSON file.

        Args:
            json_path: Path to JSON file.

        Returns:
            Dictionary of extracted metrics.
        """
        path = Path(json_path)
        if not path.exists():
            return {}

        try:
            with open(path) as f:
                data = json.load(f)

            # Extract numeric metrics
            metrics = {}
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    metrics[key] = value
                elif isinstance(value, str):
                    # Try to parse as number
                    try:
                        if "." in value:
                            metrics[key] = float(value)
                        else:
                            metrics[key] = int(value)
                    except ValueError:
                        metrics[key] = value

            return metrics
        except Exception:
            return {}

    def get_training_progress(
        self,
        log_path: str,
    ) -> dict[str, Any]:
        """Get training progress information.

        Args:
            log_path: Path to log file.

        Returns:
            Dictionary with progress info.
        """
        log_content = self._read_log(log_path)

        # Extract epoch progress
        epoch_pattern = r"epoch[:\s]+(\d+)"
        epochs = re.findall(epoch_pattern, log_content, re.IGNORECASE)

        # Extract step/iteration progress
        step_pattern = r"step[:\s]+(\d+)"
        steps = re.findall(step_pattern, log_content, re.IGNORECASE)

        # Extract percentage
        progress_pattern = r"progress[:\s]+(\d+(?:\.\d+)?)%"
        percentages = re.findall(progress_pattern, log_content, re.IGNORECASE)

        return {
            "last_epoch": int(epochs[-1]) if epochs else None,
            "total_epochs": max(map(int, epochs)) if epochs else None,
            "last_step": int(steps[-1]) if steps else None,
            "total_steps": max(map(int, steps)) if steps else None,
            "last_progress_percent": float(percentages[-1]) if percentages else None,
        }

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

    def _get_default_patterns(self) -> dict[str, str]:
        """Get default regex patterns for common metrics.

        Returns:
            Dictionary of metric name to pattern.
        """
        return {
            # Loss metrics
            "train_loss": r"train[_\s]loss[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "val_loss": r"val(?:idation)?[_\s]loss[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "test_loss": r"test[_\s]loss[:\s]+([0-9]+(?:\.[0-9]+)?)",

            # Accuracy metrics
            "train_acc": r"train[_\s]acc(?:uracy)?[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "val_acc": r"val(?:idation)?[_\s]acc(?:uracy)?[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "test_acc": r"test[_\s]acc(?:uracy)?[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "accuracy": r"accuracy[:\s]+([0-9]+(?:\.[0-9]+)?)",

            # Time metrics
            "epoch_time": r"epoch[_\s]time[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "total_time": r"total[_\s]time[:\s]+([0-9]+(?:\.[0-9]+)?)",

            # Resource metrics
            "gpu_memory": r"gpu[_\s]memory[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "memory_mb": r"memory[:\s]+([0-9]+(?:\.[0-9]+)?)",

            # F1 score
            "f1_score": r"f1[_\s]score[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "f1": r"f1[:\s]+([0-9]+(?:\.[0-9]+)?)",

            # Precision/Recall
            "precision": r"precision[:\s]+([0-9]+(?:\.[0-9]+)?)",
            "recall": r"recall[:\s]+([0-9]+(?:\.[0-9]+)?)",

            # Learning rate
            "learning_rate": r"learning[_\s]rate[:\s]+([0-9]+(?:\.[0-9]+(?:e[+-]?[0-9]+)?)?)",
            "lr": r"\blr[:\s]+([0-9]+(?:\.[0-9]+(?:e[+-]?[0-9]+)?)?)",
        }

    def add_pattern(self, metric_name: str, pattern: str) -> None:
        """Add a custom pattern.

        Args:
            metric_name: Name for the metric.
            pattern: Regex pattern.
        """
        self.patterns[metric_name] = pattern

    def remove_pattern(self, metric_name: str) -> None:
        """Remove a pattern.

        Args:
            metric_name: Metric name to remove.
        """
        if metric_name in self.patterns:
            del self.patterns[metric_name]
