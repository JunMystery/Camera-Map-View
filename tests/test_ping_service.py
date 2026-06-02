"""Tests for background camera connectivity checks."""

from PyQt6.QtCore import QCoreApplication

from controllers.camera_data_manager import CameraDataManager
from models.camera_data_model import Camera
from services.active_ping_service import open_active_ping
from services.network_ping_service import PingService


def test_ping_service_uses_icmp_latency_when_available() -> None:
    service = PingService(
        ping_func=lambda ip, timeout: 0.012,
        tcp_check_func=lambda ip, port, timeout: False,
    )

    is_online, latency = service.check_camera(Camera("cam", "Lobby", "10.0.0.10"))

    assert is_online is True
    assert latency == 12.0


def test_ping_service_falls_back_to_tcp_when_ping_fails() -> None:
    service = PingService(
        ping_func=lambda ip, timeout: None,
        tcp_check_func=lambda ip, port, timeout: True,
    )

    is_online, latency = service.check_camera(Camera("cam", "Lobby", "10.0.0.10"))

    assert is_online is True
    assert latency == 0.0


def test_ping_service_reports_offline_when_all_checks_fail() -> None:
    service = PingService(
        ping_func=lambda ip, timeout: None,
        tcp_check_func=lambda ip, port, timeout: False,
    )

    is_online, latency = service.check_camera(Camera("cam", "Lobby", "10.0.0.10"))

    assert is_online is False
    assert latency == -1.0


def test_run_once_emits_status_without_real_network() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    service = PingService(
        [Camera("cam", "Lobby", "10.0.0.10")],
        ping_func=lambda ip, timeout: 0.001,
        tcp_check_func=lambda ip, port, timeout: False,
    )
    emitted: list[tuple[str, bool, float]] = []
    service.status_updated.connect(lambda camera_id, online, latency: emitted.append((camera_id, online, latency)))

    service.run_once()

    assert emitted == [("cam", True, 1.0)]
    app.processEvents()


def test_camera_manager_persists_status_and_ping_history() -> None:
    manager = CameraDataManager(":memory:")
    manager.db.execute(
        "INSERT OR IGNORE INTO map_layouts (id, name, background_path) VALUES (?, ?, ?)",
        ("default", "Default Layout", ""),
    )
    manager.add_camera(Camera("cam", "Lobby", "10.0.0.10"))

    assert manager.update_camera_status("cam", True, 3.5)

    saved = manager.get_camera("cam")
    history = manager.get_ping_history("cam")
    assert saved is not None
    assert saved.status is True
    assert saved.last_check is not None
    assert len(history) == 1
    assert history[0]["is_online"] is True
    assert history[0]["latency"] == 3.5


def test_ping_service_retries_before_offline() -> None:
    attempts = 0

    def tcp_check(ip_address: str, port: int, timeout: float) -> bool:
        nonlocal attempts
        attempts += 1
        return attempts == 2

    service = PingService(
        [Camera("cam", "Lobby", "10.0.0.10")],
        ping_func=lambda ip, timeout: None,
        tcp_check_func=tcp_check,
        retries=2,
    )

    assert service.check_camera(Camera("cam", "Lobby", "10.0.0.10")) == (True, 0.0)
    assert attempts == 2


def test_active_ping_opens_windows_continuous_ping(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr("services.active_ping_service.platform.system", lambda: "Windows")
    monkeypatch.setattr("services.active_ping_service.subprocess.Popen", lambda command, creationflags=0: calls.append((command, creationflags)))

    assert open_active_ping("10.0.0.10")

    assert calls[0][0] == ["cmd.exe", "/k", "ping", "-t", "10.0.0.10"]


def test_active_ping_rejects_invalid_ip() -> None:
    assert not open_active_ping("999.0.0.10")
