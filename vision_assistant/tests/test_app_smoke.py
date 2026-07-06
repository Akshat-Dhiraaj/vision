from __future__ import annotations

import subprocess
import sys


def test_cli_version_command_runs_without_camera() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "vision_assistant.app", "--version"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "vision-assistant 0.1.0" in result.stdout


def test_cli_check_config_runs_without_camera() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "vision_assistant.app", "--check-config"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "Config OK: 1 action(s) loaded." in result.stdout
