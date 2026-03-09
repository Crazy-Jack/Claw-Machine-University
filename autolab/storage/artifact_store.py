"""Artifact store for managing experiment artifacts."""

import shutil
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Artifact(BaseModel):
    """Represents an artifact from an experiment."""

    name: str = Field(..., description="Artifact name")
    path: str = Field(..., description="Relative path to artifact")
    type: str = Field(..., description="Artifact type (model, checkpoint, log, plot, etc.)")
    size_bytes: int | None = Field(None, description="Artifact size in bytes")
    created_at: str = Field(..., description="ISO timestamp of creation")


class ArtifactStore:
    """Storage for experiment artifacts."""

    def __init__(self, workspace_path: str = "./autolab_workspace") -> None:
        """Initialize the artifact store.

        Args:
            workspace_path: Path to the workspace directory.
        """
        self.workspace_path = Path(workspace_path).expanduser().resolve()
        self.artifacts_dir = self.workspace_path / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def get_experiment_dir(self, experiment_id: str) -> Path:
        """Get the directory for a specific experiment.

        Args:
            experiment_id: ID of experiment.

        Returns:
            Path to experiment directory.
        """
        exp_dir = self.artifacts_dir / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        return exp_dir

    def save_artifact(
        self,
        experiment_id: str,
        source_path: str | Path,
        artifact_name: str,
        artifact_type: str,
    ) -> Artifact:
        """Save an artifact for an experiment.

        Args:
            experiment_id: ID of experiment.
            source_path: Path to source file.
            artifact_name: Name for the artifact.
            artifact_type: Type of artifact.

        Returns:
            Artifact object.

        Raises:
            FileNotFoundError: If source file doesn't exist.
        """
        from datetime import datetime

        source = Path(source_path).expanduser().resolve()
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        exp_dir = self.get_experiment_dir(experiment_id)
        dest_path = exp_dir / artifact_name

        # Copy the artifact
        shutil.copy2(source, dest_path)

        # Get file size
        size_bytes = dest_path.stat().st_size if dest_path.exists() else None

        # Create artifact object
        artifact = Artifact(
            name=artifact_name,
            path=str(dest_path.relative_to(self.workspace_path)),
            type=artifact_type,
            size_bytes=size_bytes,
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        # Save artifact metadata
        self._save_artifact_metadata(experiment_id, artifact)

        return artifact

    def save_text_as_artifact(
        self,
        experiment_id: str,
        content: str,
        artifact_name: str,
        artifact_type: str,
    ) -> Artifact:
        """Save text content as an artifact.

        Args:
            experiment_id: ID of experiment.
            content: Text content to save.
            artifact_name: Name for the artifact.
            artifact_type: Type of artifact.

        Returns:
            Artifact object.
        """
        from datetime import datetime

        exp_dir = self.get_experiment_dir(experiment_id)
        dest_path = exp_dir / artifact_name

        # Write content to file
        with open(dest_path, "w") as f:
            f.write(content)

        # Get file size
        size_bytes = dest_path.stat().st_size if dest_path.exists() else None

        # Create artifact object
        artifact = Artifact(
            name=artifact_name,
            path=str(dest_path.relative_to(self.workspace_path)),
            type=artifact_type,
            size_bytes=size_bytes,
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        # Save artifact metadata
        self._save_artifact_metadata(experiment_id, artifact)

        return artifact

    def _save_artifact_metadata(self, experiment_id: str, artifact: Artifact) -> None:
        """Save artifact metadata.

        Args:
            experiment_id: ID of experiment.
            artifact: Artifact object.
        """
        import json

        exp_dir = self.get_experiment_dir(experiment_id)
        metadata_file = exp_dir / "artifacts.json"

        # Load existing metadata
        artifacts = []
        if metadata_file.exists():
            with open(metadata_file) as f:
                artifacts = json.load(f)

        # Add new artifact
        artifacts.append(artifact.model_dump())

        # Save metadata
        with open(metadata_file, "w") as f:
            json.dump(artifacts, f, indent=2)

    def get_artifacts(self, experiment_id: str) -> list[Artifact]:
        """Get all artifacts for an experiment.

        Args:
            experiment_id: ID of experiment.

        Returns:
            List of Artifact objects.
        """
        import json

        exp_dir = self.get_experiment_dir(experiment_id)
        metadata_file = exp_dir / "artifacts.json"

        if not metadata_file.exists():
            return []

        with open(metadata_file) as f:
            data = json.load(f)

        return [Artifact(**a) for a in data]

    def get_artifact_path(self, experiment_id: str, artifact_name: str) -> Path | None:
        """Get path to a specific artifact.

        Args:
            experiment_id: ID of experiment.
            artifact_name: Name of artifact.

        Returns:
            Path to artifact or None if not found.
        """
        artifacts = self.get_artifacts(experiment_id)

        for artifact in artifacts:
            if artifact.name == artifact_name:
                return self.workspace_path / artifact.path

        return None

    def delete_experiment_artifacts(self, experiment_id: str) -> None:
        """Delete all artifacts for an experiment.

        Args:
            experiment_id: ID of experiment.
        """
        exp_dir = self.get_experiment_dir(experiment_id)
        if exp_dir.exists():
            shutil.rmtree(exp_dir)

    def copy_to_experiment(
        self,
        source_experiment_id: str,
        dest_experiment_id: str,
        artifact_name: str,
    ) -> Artifact | None:
        """Copy an artifact from one experiment to another.

        Args:
            source_experiment_id: ID of source experiment.
            dest_experiment_id: ID of destination experiment.
            artifact_name: Name of artifact to copy.

        Returns:
            New Artifact object or None if not found.
        """
        source_path = self.get_artifact_path(source_experiment_id, artifact_name)
        if source_path is None:
            return None

        artifacts = self.get_artifacts(source_experiment_id)
        artifact = next((a for a in artifacts if a.name == artifact_name), None)

        if artifact is None:
            return None

        return self.save_artifact(
            dest_experiment_id,
            source_path,
            artifact_name,
            artifact.type,
        )
