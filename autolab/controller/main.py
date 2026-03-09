"""Main entry point for the autonomous lab controller."""

import argparse
import sys
from pathlib import Path


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Autolab Autonomous ML Research Controller",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--workspace",
        default="./autolab_workspace",
        help="Path to workspace directory",
    )
    parser.add_argument(
        "--config-dir",
        default="./autolab/configs",
        help="Path to configuration directory",
    )
    parser.add_argument(
        "--loop-interval",
        type=float,
        default=60.0,
        help="Interval between loop cycles in seconds",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key for AI provider (or set ANTHROPIC_API_KEY or ZAI_API_KEY env var)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no actions applied)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run single cycle and exit",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Get API key from environment if not provided
    import os

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ZAI_API_KEY")

    if not api_key:
        print("Warning: No API key provided. AI integration will be disabled.")
        print("Set ANTHROPIC_API_KEY (for Claude) or ZAI_API_KEY (for GLM-4.7) environment variable.")
        print("Or set api_key in configs/openclaw.yaml")
        print("You can also use --api-key flag as override.")
    else:
        provider = os.environ.get("ANTHROPIC_API_KEY", "zai") if os.environ.get("ZAI_API_KEY") else "anthropic"
        print(f"Using API key from environment (provider: {provider if api_key == os.environ.get('ZAI_API_KEY') else 'anthropic'})")

    # Import after argparse to avoid slow imports if --help is used
    from autolab.controller.loop import MainLoop

    # Create main loop
    loop = MainLoop(
        workspace_path=args.workspace,
        config_path=args.config_dir,
        loop_interval_seconds=args.loop_interval,
        api_key=api_key,
    )

    if args.once:
        # Run single cycle
        print("Running single cycle...")
        loop.run_cycle()
        return 0
    else:
        # Run continuous loop
        try:
            loop.run()
        except KeyboardInterrupt:
            print("\nReceived interrupt signal")
            loop.shutdown()
        except Exception as e:
            print(f"Fatal error: {e}")
            import traceback

            traceback.print_exc()
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
