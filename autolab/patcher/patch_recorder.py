"""Patch recorder for tracking all applied patches."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class PatchRecorder:
    """Record and track all applied patches."""

    def __init__(self, workspace_path: str = "./autolab_workspace") -> None:
        """Initialize patch recorder.

        Args:
            workspace_path: Path to workspace directory.
        """
        self.workspace_path = Path(workspace_path).expanduser().resolve()
        self.patches_dir = self.workspace_path / "patches"
        self.patches_dir.mkdir(parents=True, exist_ok=True)

        self.patch_log_file = self.patches_dir / "patch_log.json"

    def record_patch(
        self,
        experiment_id: str,
        patch_type: str,  # "config" or "code"
        target: str,  # For code: file_path, for config: experiment_id
        patch_data: dict[str, Any],
        status: str = "applied",
        error_message: str = "",
    ) -> dict[str, Any]:
        """Record a patch application.

        Args:
            experiment_id: Experiment ID.
            patch_type: Type of patch ("config" or "code").
            target: Target of patch.
            patch_data: Patch data.
            status: Status ("applied", "failed", "dry_run").
            error_message: Error message if failed.

        Returns:
            Recorded patch entry.
        """
        patch_entry = {
            "id": self._generate_patch_id(),
            "experiment_id": experiment_id,
            "patch_type": patch_type,
            "target": target,
            "patch_data": patch_data,
            "status": status,
            "error_message": error_message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        # Load existing log
        log = self._load_log()

        # Add new entry
        log.append(patch_entry)

        # Save log
        self._save_log(log)

        # Save individual patch file
        self._save_patch_file(patch_entry)

        return patch_entry

    def get_patches_for_experiment(
        self,
        experiment_id: str,
    ) -> list[dict[str, Any]]:
        """Get all patches for an experiment.

        Args:
            experiment_id: Experiment ID.

        Returns:
            List of patch entries.
        """
        log = self._load_log()

        return [
            entry
            for entry in log
            if entry["experiment_id"] == experiment_id
        ]

    def get_patches_for_target(
        self,
        target: str,
        patch_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all patches for a target.

        Args:
            target: Target (file_path or experiment_id).
            patch_type: Optional filter by patch type.

        Returns:
            List of patch entries.
        """
        log = self._load_log()

        patches = [
            entry
            for entry in log
            if entry["target"] == target
        ]

        if patch_type:
            patches = [
                entry
                for entry in patches
                if entry["patch_type"] == patch_type
            ]

        return patches

    def get_recent_patches(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get recent patches.

        Args:
            limit: Maximum number of patches to return.

        Returns:
            List of recent patch entries.
        """
        log = self._load_log()

        # Sort by timestamp descending
        sorted_log = sorted(
            log,
            key=lambda x: x["timestamp"],
            reverse=True,
        )

        return sorted_log[:limit]

    def get_patch_by_id(
        self,
        patch_id: str,
    ) -> dict[str, Any] | None:
        """Get a patch by ID.

        Args:
            patch_id: Patch ID.

        Returns:
            Patch entry or None if not found.
        """
        log = self._load_log()

        for entry in log:
            if entry["id"] == patch_id:
                return entry

        return None

    def revert_patch(
        self,
        patch_id: str,
    ) -> dict[str, Any]:
        """Revert a patch (mark as reverted).

        Args:
            patch_id: Patch ID.

        Returns:
            Updated patch entry.

        Raises:
            ValueError: If patch not found.
        """
        log = self._load_log()

        for i, entry in enumerate(log):
            if entry["id"] == patch_id:
                # Update status
                log[i]["status"] = "reverted"
                log[i]["reverted_at"] = datetime.utcnow().isoformat() + "Z"

                # Save log
                self._save_log(log)

                return log[i]

        raise ValueError(f"Patch not found: {patch_id}")

    def get_statistics(self) -> dict[str, Any]:
        """Get patch statistics.

        Returns:
            Statistics dictionary.
        """
        log = self._load_log()

        total = len(log)

        by_type = {}
        by_status = {}
        by_experiment = {}

        for entry in log:
            # Count by type
            patch_type = entry["patch_type"]
            by_type[patch_type] = by_type.get(patch_type, 0) + 1

            # Count by status
            status = entry["status"]
            by_status[status] = by_status.get(status, 0) + 1

            # Count by experiment
            exp_id = entry["experiment_id"]
            by_experiment[exp_id] = by_experiment.get(exp_id, 0) + 1

        return {
            "total_patches": total,
            "by_type": by_type,
            "by_status": by_status,
            "by_experiment": by_experiment,
        }

    def _generate_patch_id(self) -> str:
        """Generate a unique patch ID.

        Returns:
            Patch ID string.
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        # Simple counter (in production, use UUID or similar)
        return f"patch_{timestamp}"

    def _load_log(self) -> list[dict[str, Any]]:
        """Load patch log from disk.

        Returns:
            List of patch entries.
        """
        if not self.patch_log_file.exists():
            return []

        with open(self.patch_log_file) as f:
            return json.load(f)

    def _save_log(self, log: list[dict[str, Any]]) -> None:
        """Save patch log to disk.

        Args:
            log: List of patch entries.
        """
        with open(self.patch_log_file, "w") as f:
            json.dump(log, f, indent=2)

    def _save_patch_file(self, patch_entry: dict[str, Any]) -> None:
        """Save individual patch file.

        Args:
            patch_entry: Patch entry to save.
        """
        patch_id = patch_entry["id"]
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        filename = f"{patch_id}_{timestamp}.json"
        patch_path = self.patches_dir / filename

        with open(patch_path, "w") as f:
            json.dump(patch_entry, f, indent=2)
