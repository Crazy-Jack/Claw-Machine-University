"""Heartbeat monitoring for controller health."""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class Heartbeat:
    """Heartbeat monitor for controller."""

    def __init__(
        self,
        heartbeat_path: str = "./autolab_workspace/state/heartbeat.txt",
        interval_seconds: float = 60.0,
        pid: int | None = None,
    ) -> None:
        """Initialize heartbeat monitor.

        Args:
            heartbeat_path: Path to heartbeat file.
            interval_seconds: Interval between heartbeats.
            pid: Process ID (or auto-detect).
        """
        self.heartbeat_path = Path(heartbeat_path).expanduser().resolve()
        self.interval_seconds = interval_seconds
        self.pid = pid or os.getpid()
        self.start_time = time.time()
        self.last_heartbeat_time = 0.0
        self.cycle_count = 0

        # Ensure directory exists
        self.heartbeat_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self) -> None:
        """Write heartbeat to file."""
        now = time.time()

        # Only write if interval has passed
        if now - self.last_heartbeat_time < self.interval_seconds:
            return

        self.last_heartbeat_time = now
        uptime = now - self.start_time

        heartbeat_data = {
            "pid": self.pid,
            "uptime_seconds": uptime,
            "uptime_human": self._format_uptime(uptime),
            "cycle_count": self.cycle_count,
            "last_update": datetime.utcnow().isoformat() + "Z",
        }

        with open(self.heartbeat_path, "w") as f:
            for key, value in heartbeat_data.items():
                f.write(f"{key}={value}\n")

    def update_cycle_count(self, count: int) -> None:
        """Update cycle count.

        Args:
            count: New cycle count.
        """
        self.cycle_count = count
        self.write()

    def increment_cycle_count(self) -> None:
        """Increment cycle count."""
        self.cycle_count += 1
        self.write()

    def read(self) -> dict[str, Any] | None:
        """Read heartbeat file.

        Returns:
            Heartbeat data or None if file doesn't exist.
        """
        if not self.heartbeat_path.exists():
            return None

        data = {}
        with open(self.heartbeat_path) as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    data[key] = value

        return data

    def is_alive(
        self,
        timeout_seconds: float = 300.0,
    ) -> bool:
        """Check if controller is alive based on heartbeat.

        Args:
            timeout_seconds: Timeout before considering dead.

        Returns:
            True if alive.
        """
        data = self.read()
        if not data:
            return False

        try:
            last_update_str = data.get("last_update")
            if not last_update_str:
                return False

            last_update = datetime.fromisoformat(last_update_str.replace("Z", "+00:00"))
            elapsed = (datetime.utcnow() - last_update).total_seconds()

            return elapsed < timeout_seconds
        except Exception:
            return False

    def get_pid(self) -> int | None:
        """Get PID from heartbeat.

        Returns:
            PID or None.
        """
        data = self.read()
        if not data:
            return None

        try:
            return int(data.get("pid", 0))
        except (ValueError, TypeError):
            return None

    def get_uptime(self) -> float | None:
        """Get uptime from heartbeat.

        Returns:
            Uptime in seconds or None.
        """
        data = self.read()
        if not data:
            return None

        try:
            return float(data.get("uptime_seconds", 0))
        except (ValueError, TypeError):
            return None

    def get_cycle_count(self) -> int | None:
        """Get cycle count from heartbeat.

        Returns:
            Cycle count or None.
        """
        data = self.read()
        if not data:
            return None

        try:
            return int(data.get("cycle_count", 0))
        except (ValueError, TypeError):
            return None

    def clear(self) -> None:
        """Clear heartbeat file."""
        if self.heartbeat_path.exists():
            self.heartbeat_path.unlink()

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable form.

        Args:
            seconds: Uptime in seconds.

        Returns:
            Formatted string.
        """
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.0f}m"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.1f}h"
        else:
            days = seconds / 86400
            return f"{days:.1f}d"


class HeartbeatMonitor:
    """Monitor for checking heartbeat health."""

    def __init__(
        self,
        heartbeat_path: str = "./autolab_workspace/state/heartbeat.txt",
        timeout_seconds: float = 300.0,
    ) -> None:
        """Initialize heartbeat monitor.

        Args:
            heartbeat_path: Path to heartbeat file.
            timeout_seconds: Timeout before considering dead.
        """
        self.heartbeat_path = heartbeat_path
        self.timeout_seconds = timeout_seconds

    def check(self) -> dict[str, Any]:
        """Check heartbeat status.

        Returns:
            Dictionary with status information.
        """
        heartbeat = Heartbeat(heartbeat_path=self.heartbeat_path)

        is_alive = heartbeat.is_alive(self.timeout_seconds)

        data = {
            "alive": is_alive,
            "pid": heartbeat.get_pid(),
            "uptime": heartbeat.get_uptime(),
            "cycle_count": heartbeat.get_cycle_count(),
            "last_check": datetime.utcnow().isoformat() + "Z",
        }

        if not is_alive:
            data["status"] = "dead"
        else:
            data["status"] = "alive"

        return data

    def wait_for_heartbeat(
        self,
        max_wait_seconds: float = 60.0,
        check_interval: float = 1.0,
    ) -> bool:
        """Wait for heartbeat to appear.

        Args:
            max_wait_seconds: Maximum time to wait.
            check_interval: Interval between checks.

        Returns:
            True if heartbeat appeared.
        """
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            heartbeat = Heartbeat(heartbeat_path=self.heartbeat_path)
            if heartbeat.read() is not None:
                return True

            time.sleep(check_interval)

        return False

    def wait_for_death(
        self,
        max_wait_seconds: float = 60.0,
        check_interval: float = 1.0,
    ) -> bool:
        """Wait for heartbeat to disappear.

        Args:
            max_wait_seconds: Maximum time to wait.
            check_interval: Interval between checks.

        Returns:
            True if heartbeat disappeared.
        """
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            heartbeat = Heartbeat(heartbeat_path=self.heartbeat_path)
            if not heartbeat.is_alive():
                return True

            time.sleep(check_interval)

        return False
