"""Autolab - Autonomous ML Experiment Framework.

A production-grade autonomous ML research system that integrates OpenClaw
for planning with deterministic orchestration for experiment management.
"""

__version__ = "0.1.0"

from autolab.schemas.experiment import Experiment
from autolab.schemas.result import Result
from autolab.schemas.hypothesis import Hypothesis
from autolab.schemas.action import PlannerAction
from autolab.schemas.state import GlobalState, LabStatus
from autolab.schemas.worker import Worker, GPUInfo

__all__ = [
    "Experiment",
    "Result",
    "Hypothesis",
    "PlannerAction",
    "GlobalState",
    "LabStatus",
    "Worker",
    "GPUInfo",
]


def main() -> None:
    """Entry point for autolab CLI."""
    import sys

    from autolab.controller.main import main as controller_main

    sys.exit(controller_main())
