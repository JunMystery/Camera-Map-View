"""Background network monitor for camera connectivity."""

import socket
import time
from collections.abc import Callable

from PyQt6.QtCore import QMutex, QMutexLocker, QThread, pyqtSignal

from models.camera_data_model import Camera

try:
    from ping3 import ping as default_ping
except ImportError:  # pragma: no cover - dependency is declared in requirements.
    default_ping = None


PingFunction = Callable[[str, float], float | None]
TcpCheckFunction = Callable[[str, int, float], bool]


class PingService(QThread):
    """Check camera reachability without blocking the UI thread."""

    status_updated = pyqtSignal(str, bool, float)

    def __init__(
        self,
        cameras: list[Camera] | None = None,
        interval_seconds: int = 30,
        timeout_seconds: float = 1.0,
        retries: int = 1,
        ping_func: PingFunction | None = None,
        tcp_check_func: TcpCheckFunction | None = None,
    ) -> None:
        super().__init__()
        self.interval_seconds = interval_seconds
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.ping_func = ping_func or self._default_ping
        self.tcp_check_func = tcp_check_func or self.check_tcp_port
        self._mutex = QMutex()
        self._cameras = list(cameras or [])
        self._running = False

    def set_cameras(self, cameras: list[Camera]) -> None:
        """Replace the monitored camera snapshot."""
        with QMutexLocker(self._mutex):
            self._cameras = list(cameras)

    def stop(self) -> None:
        """Stop the worker thread."""
        self._running = False
        if self.isRunning():
            self.wait(2000)

    def check_camera(self, camera: Camera) -> tuple[bool, float]:
        """Check one camera with ICMP first, then TCP fallback."""
        for _ in range(max(1, self.retries)):
            latency = self.check_ping(camera.ip_address)
            if latency is not None:
                return True, latency

            if self.tcp_check_func(camera.ip_address, camera.port, self.timeout_seconds):
                return True, 0.0

        return False, -1.0

    def update_settings(self, interval_seconds: int, timeout_seconds: float, retries: int) -> None:
        """Update runtime network monitoring settings."""
        self.interval_seconds = interval_seconds
        self.timeout_seconds = timeout_seconds
        self.retries = retries

    def check_ping(self, ip_address: str) -> float | None:
        """Return ping latency in milliseconds, or None when ICMP fails."""
        try:
            delay_seconds = self.ping_func(ip_address, self.timeout_seconds)
        except Exception:
            return None

        if delay_seconds is None:
            return None
        return float(delay_seconds) * 1000.0

    def check_tcp_port(self, ip_address: str, port: int, timeout_seconds: float) -> bool:
        """Fallback reachability check using a short TCP connect."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout_seconds)
                return sock.connect_ex((ip_address, port)) == 0
        except Exception:
            return False

    def run_once(self) -> None:
        """Run one monitoring pass and emit status for each camera."""
        cameras = self._snapshot_cameras()
        for camera in cameras:
            if not self._running and self.isRunning():
                break
            is_online, latency_ms = self.check_camera(camera)
            self.status_updated.emit(camera.id, is_online, latency_ms)

    def run(self) -> None:
        """Continuously monitor cameras until stopped."""
        self._running = True
        while self._running:
            self.run_once()
            self._sleep_interval()

    def _snapshot_cameras(self) -> list[Camera]:
        with QMutexLocker(self._mutex):
            return list(self._cameras)

    def _sleep_interval(self) -> None:
        deadline = time.monotonic() + self.interval_seconds
        while self._running and time.monotonic() < deadline:
            self.msleep(100)

    def _default_ping(self, ip_address: str, timeout_seconds: float) -> float | None:
        if default_ping is None:
            return None
        return default_ping(ip_address, timeout=timeout_seconds)
