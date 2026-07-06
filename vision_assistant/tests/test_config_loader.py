from __future__ import annotations

from pathlib import Path

import pytest

from vision_assistant.src.config_loader import (
    ConfigError,
    load_config,
    validate_path,
)


def test_loads_valid_project_config() -> None:
    config = load_config()

    assert config.settings.app_name == "vision_assistant"
    assert config.settings.camera_index == 0
    assert set(config.actions) == {"open_test_page"}
    assert config.actions["open_test_page"].url == "https://example.com"


def test_rejects_missing_action_fields(tmp_path: Path) -> None:
    write_settings(tmp_path)
    write_actions(
        tmp_path,
        """
actions:
  open_test_page:
    type: website
    confirm: false
""",
    )

    with pytest.raises(ConfigError, match="url"):
        load_config(tmp_path)


def test_rejects_non_allowlisted_action_names(tmp_path: Path) -> None:
    write_settings(tmp_path)
    write_actions(
        tmp_path,
        """
actions:
  open_youtube:
    type: website
    url: "https://www.youtube.com"
    confirm: false
""",
    )

    with pytest.raises(ConfigError, match="not allowlisted"):
        load_config(tmp_path)


def test_rejects_invalid_urls(tmp_path: Path) -> None:
    write_settings(tmp_path)
    write_actions(
        tmp_path,
        """
actions:
  open_test_page:
    type: website
    url: "ftp://example.com"
    confirm: false
""",
    )

    with pytest.raises(ConfigError, match="http or https"):
        load_config(tmp_path)


def test_rejects_relative_paths() -> None:
    with pytest.raises(ConfigError, match="absolute"):
        validate_path("relative/path")


def write_settings(tmp_path: Path) -> None:
    (tmp_path / "settings.yaml").write_text(
        """
app:
  name: vision_assistant
  version: "0.1.0"
camera:
  default_index: 0
stability:
  min_duration_ms: 400
  action_cooldown_ms: 5000
lmstudio:
  base_url: "http://localhost:1234/v1"
safety:
  allowed_action_names:
    - open_test_page
  allowed_action_types:
    - website
""",
        encoding="utf-8",
    )


def write_actions(tmp_path: Path, content: str) -> None:
    (tmp_path / "actions.yaml").write_text(content, encoding="utf-8")
