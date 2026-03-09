"""Git snapshot functionality for code versioning."""

import json
import os
import subprocess
from pathlib import Path
from typing import Any


class GitSnapshot:
    """Snapshot git state for experiments."""

    def __init__(self, repo_path: str = ".") -> None:
        """Initialize git snapshot.

        Args:
            repo_path: Path to git repository.
        """
        self.repo_path = Path(repo_path).expanduser().resolve()

    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository.

        Returns:
            True if in a git repository.
        """
        return (self.repo_path / ".git").exists()

    def get_snapshot(self) -> dict[str, Any]:
        """Get git snapshot information.

        Returns:
            Dictionary with git state information.
        """
        if not self.is_git_repo():
            return {"is_git_repo": False}

        try:
            # Get commit hash
            commit_hash = self._run_git_command(["git", "rev-parse", "HEAD"])

            # Get branch name
            branch = self._run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])

            # Check if working directory is dirty
            dirty = bool(self._run_git_command(["git", "status", "--porcelain"]))

            # Get commit message
            commit_message = self._run_git_command(["git", "log", "-1", "--pretty=%B"]).strip()

            # Get commit date
            commit_date = self._run_git_command(["git", "log", "-1", "--pretty=%ci"]).strip()

            # Get remote URL if available
            try:
                remote_url = self._run_git_command(["git", "config", "--get", "remote.origin.url"])
            except subprocess.CalledProcessError:
                remote_url = None

            return {
                "is_git_repo": True,
                "commit_hash": commit_hash,
                "branch": branch,
                "is_dirty": dirty,
                "commit_message": commit_message,
                "commit_date": commit_date,
                "remote_url": remote_url,
                "repo_path": str(self.repo_path),
            }
        except Exception as e:
            return {
                "is_git_repo": True,
                "error": str(e),
                "repo_path": str(self.repo_path),
            }

    def get_untracked_files(self) -> list[str]:
        """Get list of untracked files.

        Returns:
            List of untracked file paths.
        """
        if not self.is_git_repo():
            return []

        try:
            output = self._run_git_command(["git", "ls-files", "--others", "--exclude-standard"])
            return output.split("\n") if output else []
        except Exception:
            return []

    def get_modified_files(self) -> list[str]:
        """Get list of modified files.

        Returns:
            List of modified file paths.
        """
        if not self.is_git_repo():
            return []

        try:
            output = self._run_git_command(["git", "diff", "--name-only"])
            return output.split("\n") if output else []
        except Exception:
            return []

    def save_snapshot(
        self,
        experiment_id: str,
        artifact_store_path: str = "./autolab_workspace",
    ) -> str | None:
        """Save git snapshot to file.

        Args:
            experiment_id: ID of experiment.
            artifact_store_path: Path to artifact store.

        Returns:
            Path to saved snapshot file or None if not a git repo.
        """
        snapshot = self.get_snapshot()
        if not snapshot.get("is_git_repo"):
            return None

        # Save to experiment artifacts
        workspace = Path(artifact_store_path).expanduser().resolve()
        exp_dir = workspace / "artifacts" / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        snapshot_path = exp_dir / "git_snapshot.json"

        with open(snapshot_path, "w") as f:
            json.dump(snapshot, f, indent=2)

        return str(snapshot_path)

    def create_diff(self, experiment_id: str, artifact_store_path: str = "./autolab_workspace") -> str | None:
        """Create a diff file for uncommitted changes.

        Args:
            experiment_id: ID of experiment.
            artifact_store_path: Path to artifact store.

        Returns:
            Path to diff file or None if no changes.
        """
        if not self.is_git_repo():
            return None

        try:
            # Get diff
            diff_output = self._run_git_command(["git", "diff"])

            if not diff_output:
                return None

            # Save to experiment artifacts
            workspace = Path(artifact_store_path).expanduser().resolve()
            exp_dir = workspace / "artifacts" / experiment_id
            exp_dir.mkdir(parents=True, exist_ok=True)

            diff_path = exp_dir / "uncommitted_changes.diff"

            with open(diff_path, "w") as f:
                f.write(diff_output)

            return str(diff_path)
        except Exception:
            return None

    def restore_snapshot(
        self,
        snapshot_path: str,
        working_dir: str | None = None,
    ) -> bool:
        """Restore working directory to a snapshot.

        Args:
            snapshot_path: Path to git snapshot file.
            working_dir: Working directory to restore in.

        Returns:
            True if successful.
        """
        if not self.is_git_repo():
            return False

        try:
            # Load snapshot
            with open(snapshot_path) as f:
                snapshot = json.load(f)

            commit_hash = snapshot.get("commit_hash")
            if not commit_hash:
                return False

            # Change to working directory if specified
            old_cwd = None
            if working_dir:
                old_cwd = os.getcwd()
                os.chdir(working_dir)

            try:
                # Checkout the commit
                subprocess.run(
                    ["git", "checkout", commit_hash],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return True
            finally:
                if old_cwd:
                    os.chdir(old_cwd)
        except Exception:
            return False

    def _run_git_command(self, command: list[str]) -> str:
        """Run a git command and return output.

        Args:
            command: Git command to run.

        Returns:
            Command output as string.

        Raises:
            subprocess.CalledProcessError: If command fails.
        """
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            cwd=self.repo_path,
        )
        return result.stdout.strip()

    def get_file_at_commit(
        self,
        file_path: str,
        commit_hash: str,
    ) -> str | None:
        """Get file content at a specific commit.

        Args:
            file_path: Path to file.
            commit_hash: Commit hash.

        Returns:
            File content or None if not found.
        """
        if not self.is_git_repo():
            return None

        try:
            result = subprocess.run(
                ["git", "show", f"{commit_hash}:{file_path}"],
                check=True,
                capture_output=True,
                text=True,
                cwd=self.repo_path,
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return None
