"""Schema-validated non-sensitive Terraform configuration resolution."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import ValidationError, validate

CONFIG_NAME = re.compile(r"^[a-z][a-z0-9-]*\.json$")
SECRET_KEY = re.compile(r"(?:secret|password|token|private[_-]?key|credential|api[_-]?key)", re.I)


class ConfigurationError(ValueError):
    """Raised when a Terraform configuration selection is invalid or unsafe."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except FileNotFoundError as error:
        raise ConfigurationError(f"Unknown configuration: {path.name}") from error
    except json.JSONDecodeError as error:
        raise ConfigurationError(f"Invalid JSON in {path.name}: {error.msg}") from error
    if not isinstance(value, dict):
        raise ConfigurationError(f"Configuration {path.name} must be a JSON object")
    return value


def _assert_no_secret_like_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if SECRET_KEY.search(str(key)):
                raise ConfigurationError(f"secret-like key is not allowed at {path}.{key}")
            _assert_no_secret_like_keys(nested_value, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            _assert_no_secret_like_keys(nested_value, f"{path}[{index}]")


def _validate(value: dict[str, Any], schema_path: Path, config_name: str) -> None:
    try:
        validate(value, _read_json(schema_path))
    except ValidationError as error:
        location = ".".join(str(part) for part in error.path) or "$"
        message = f"Schema validation failed for {config_name} at {location}: {error.message}"
        raise ConfigurationError(message) from error


def _selected_path(config_root: Path, name: str, kind: str) -> Path:
    if not CONFIG_NAME.fullmatch(name):
        raise ConfigurationError(f"Invalid {kind} configuration selection: {name}")
    path = (config_root / name).resolve()
    if path.parent != config_root.resolve() or not path.is_file():
        raise ConfigurationError(f"Unknown {kind} configuration: {name}")
    return path


def _merge(
    common: dict[str, Any], environment: dict[str, Any], project: dict[str, Any]
) -> dict[str, Any]:
    merged = {**common, **environment, **project}
    merged["labels"] = {
        **common.get("labels", {}),
        **environment.get("labels", {}),
        **project.get("labels", {}),
    }
    return merged


def resolve_config(
    config_root: Path, project_config: str, environment_config: str
) -> dict[str, Any]:
    """Return the deterministic common < environment < project configuration merge."""
    config_root = config_root.resolve()
    common_path = config_root / "common-environment.json"
    project_path = _selected_path(config_root, project_config, "project")
    environment_path = _selected_path(config_root, environment_config, "environment")
    common = _read_json(common_path)
    environment = _read_json(environment_path)
    project = _read_json(project_path)
    for value in (common, environment, project):
        _assert_no_secret_like_keys(value)
    schemas = config_root / "schemas"
    _validate(common, schemas / "common-environment.schema.json", common_path.name)
    _validate(environment, schemas / "environment.schema.json", environment_path.name)
    _validate(project, schemas / "project.schema.json", project_path.name)
    return _merge(common, environment, project)
