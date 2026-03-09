"""Autolab autonomous ML experiment framework."""

__version__ = "0.1.0"

from autolab.controller import MainLoop
from autolab.evaluator import Comparator, MetricParser
from autolab.executor import JobRunner, WorkerRegistry
from autolab.planner import ContextBuilder, OpenClawBridge
from autolab.storage import ArtifactStore, ExperimentStore, ResultStore, StateStore

__all__ = [
    "MainLoop",
    "WorkerRegistry",
    "JobRunner",
    "MetricParser",
    "Comparator",
    "ContextBuilder",
    "OpenClawBridge",
    "ExperimentStore",
    "ResultStore",
    "StateStore",
    "ArtifactStore",
]


def main() -> int:
    """Main entry point."""
    from autolab.controller.main import main as _main

    return _main()
