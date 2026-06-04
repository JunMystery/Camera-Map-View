"""Tests for the Windows EXE build script command wiring."""

import sys

from scripts import build_windows_exe


def test_build_windows_exe_command_targets_bin_and_assets() -> None:
    command = build_windows_exe.build_command()

    assert command[:3] == [sys.executable, "-m", "PyInstaller"]
    assert "--windowed" in command
    assert "--name" in command
    assert command[command.index("--name") + 1] == "CameraMapView"
    assert "--distpath" in command
    assert command[command.index("--distpath") + 1].endswith("bin")
    assert "--specpath" in command
    assert command[command.index("--specpath") + 1].endswith("build\\pyinstaller")
    assert any("assets" in value for value in command)
    assert any("config" in value for value in command)
    assert command[-1].endswith("main.py")


def test_build_windows_exe_dry_run_does_not_require_pyinstaller(capsys) -> None:
    assert build_windows_exe.main(["--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "PyInstaller" in output
    assert "CameraMapView" in output
    assert "main.py" in output
