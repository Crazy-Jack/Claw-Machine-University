"""Tool: generate_cycle_report

Generate a report for a specific cycle or range of cycles.
"""

import argparse
import sys
from pathlib import Path

from autolab.storage.experiment_store import ExperimentStore
from autolab.storage.result_store import ResultStore
from autolab.storage.state_store import StateStore
from autolab.reporting.cycle_report import CycleReportGenerator


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Generate a cycle report",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--workspace",
        default="./autolab_workspace",
        help="Path to workspace directory",
    )
    parser.add_argument(
        "--cycle",
        type=int,
        help="Specific cycle to report on (omit for latest cycle)",
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: workspace/reports/cycle_<N>.md)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "text"],
        default="markdown",
        help="Output format",
    )

    args = parser.parse_args()

    # Load data
    workspace_path = Path(args.workspace).expanduser().resolve()
    experiment_store = ExperimentStore(str(workspace_path))
    result_store = ResultStore(str(workspace_path))
    state_store = StateStore(str(workspace_path))

    experiments = experiment_store.load_all()
    results = result_store.load_all()
    state = state_store.load()

    # Determine cycle
    cycle_num = args.cycle
    if cycle_num is None:
        # Find latest cycle
        cycles = set(exp.cycle for exp in experiments.values() if exp.cycle)
        if cycles:
            cycle_num = max(cycles)
        else:
            print("No cycles found")
            return 1

    # Filter experiments by cycle
    cycle_experiments = {
        exp_id: exp
        for exp_id, exp in experiments.items()
        if exp.cycle == cycle_num
    }

    if not cycle_experiments:
        print(f"No experiments found for cycle {cycle_num}")
        return 1

    # Generate report
    generator = CycleReportGenerator(str(workspace_path))
    report = generator.generate_cycle_report(cycle_num, cycle_experiments, results, state)

    # Determine output path
    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        reports_dir = workspace_path / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        output_path = reports_dir / f"cycle_{cycle_num:03d}.md"

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)

    print(f"Report generated: {output_path}")
    print(f"Cycle: {cycle_num}")
    print(f"Experiments: {len(cycle_experiments)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
