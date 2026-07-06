from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

import yaml


DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
SUPPORTED_ACTION_TYPES = frozenset({"website", "folder", "app"})
_ACTION_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class ConfigError(ValueError):
    """Raised when config is missing, malformed, or outside the safety policy."""


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    camera_index: int
    stability_duration_ms: int
    action_cooldown_ms: int
    lmstudio_base_url: str
    allowed_action_names: frozenset[str]
    allowed_action_types: frozenset[str]


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    type: str
    confirm: bool
    url: str | None = None
    path: Path | None = None
    command: Path | None = None


@dataclass(frozen=True)
class AppConfig:
    settings: Settings
    actions: dict[str, ActionDefinition]


def load_config(config_dir: Path | str = DEFAULT_CONFIG_DIR) -> AppConfig:
    config_path = Path(config_dir)
    settings = load_settings(config_path / "settings.yaml")
    actions = load_actions(config_path / "actions.yaml", settings)
    return AppConfig(settings=settings, actions=actions)


def load_settings(path: Path | str) -> Settings:
    raw = load_yaml_file(path)

    app = require_mapping(raw, "app")
    camera = require_mapping(raw, "camera")
    stability = require_mapping(raw, "stability")
    lmstudio = require_mapping(raw, "lmstudio")
    safety = require_mapping(raw, "safety")

    allowed_names = frozenset(require_string_list(safety, "allowed_action_names"))
    if not allowed_names:
        raise ConfigError("safety.allowed_action_names must not be empty")

    for name in allowed_names:
        validate_action_name_format(name)

    allowed_types = frozenset(require_string_list(safety, "allowed_action_types"))
    unknown_types = allowed_types - SUPPORTED_ACTION_TYPES
    if unknown_types:
        raise ConfigError(
            "safety.allowed_action_types contains unsupported type(s): "
            + ", ".join(sorted(unknown_types))
        )

    return Settings(
        app_name=require_string(app, "name"),
        app_version=require_string(app, "version"),
        camera_index=require_int(camera, "default_index"),
        stability_duration_ms=require_positive_int(stability, "min_duration_ms"),
        action_cooldown_ms=require_positive_int(stability, "action_cooldown_ms"),
        lmstudio_base_url=validate_url(require_string(lmstudio, "base_url")),
        allowed_action_names=allowed_names,
        allowed_action_types=allowed_types,
    )


def load_actions(path: Path | str, settings: Settings) -> dict[str, ActionDefinition]:
    raw = load_yaml_file(path)
    actions_raw = require_mapping(raw, "actions")

    actions: dict[str, ActionDefinition] = {}
    for action_name, action_data in actions_raw.items():
        name = validate_action_name(action_name, settings.allowed_action_names)
        details = ensure_mapping(action_data, f"actions.{name}")

        action_type = require_string(details, "type")
        if action_type not in settings.allowed_action_types:
            raise ConfigError(f"actions.{name}.type is not allowlisted: {action_type}")

        confirm = require_bool(details, "confirm")
        actions[name] = build_action_definition(name, action_type, confirm, details)

    return actions


def build_action_definition(
    name: str,
    action_type: str,
    confirm: bool,
    details: dict[str, Any],
) -> ActionDefinition:
    if action_type == "website":
        return ActionDefinition(
            name=name,
            type=action_type,
            confirm=confirm,
            url=validate_url(require_string(details, "url")),
        )

    if action_type == "folder":
        return ActionDefinition(
            name=name,
            type=action_type,
            confirm=confirm,
            path=validate_path(require_string(details, "path")),
        )

    if action_type == "app":
        return ActionDefinition(
            name=name,
            type=action_type,
            confirm=confirm,
            command=validate_path(require_string(details, "command")),
        )

    raise ConfigError(f"actions.{name}.type is unsupported: {action_type}")


def load_yaml_file(path: Path | str) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file does not exist: {config_path}")

    try:
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {config_path}: {exc}") from exc

    return ensure_mapping(loaded, str(config_path))


def validate_action_name(name: Any, allowed_names: frozenset[str]) -> str:
    if not isinstance(name, str):
        raise ConfigError("Action names must be strings")

    validate_action_name_format(name)
    if name not in allowed_names:
        raise ConfigError(f"Action name is not allowlisted: {name}")

    return name


def validate_action_name_format(name: str) -> str:
    if not _ACTION_NAME_PATTERN.fullmatch(name):
        raise ConfigError(
            "Action names must start with a lowercase letter and contain only "
            "lowercase letters, numbers, and underscores"
        )
    return name


def validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ConfigError(f"URL must use http or https: {url}")

    if not parsed.netloc or parsed.username or parsed.password:
        raise ConfigError(f"URL must include a plain host: {url}")

    if any(character.isspace() for character in url):
        raise ConfigError(f"URL must not contain whitespace: {url}")

    return url


def validate_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ConfigError(f"Path must be absolute: {value}")
    return path


def require_mapping(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    if key not in mapping:
        raise ConfigError(f"Missing required config section: {key}")
    return ensure_mapping(mapping[key], key)


def ensure_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{label} must be a mapping")
    return value


def require_string(mapping: dict[str, Any], key: str) -> str:
    value = require_key(mapping, key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{key} must be a non-empty string")
    return value


def require_bool(mapping: dict[str, Any], key: str) -> bool:
    value = require_key(mapping, key)
    if not isinstance(value, bool):
        raise ConfigError(f"{key} must be true or false")
    return value


def require_int(mapping: dict[str, Any], key: str) -> int:
    value = require_key(mapping, key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"{key} must be an integer")
    return value


def require_positive_int(mapping: dict[str, Any], key: str) -> int:
    value = require_int(mapping, key)
    if value <= 0:
        raise ConfigError(f"{key} must be positive")
    return value


def require_string_list(mapping: dict[str, Any], key: str) -> list[str]:
    value = require_key(mapping, key)
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{key} must be a non-empty list")

    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ConfigError(f"{key} must contain only non-empty strings")

    return value


def require_key(mapping: dict[str, Any], key: str) -> Any:
    if key not in mapping:
        raise ConfigError(f"Missing required config field: {key}")
    return mapping[key]
