"""Packaging contract for the browser bundle served by the API."""

import tomllib
from pathlib import Path


def test_package_data_includes_nested_react_assets() -> None:
    """The installed Cloud Run package must retain Vite's assets directory."""
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    patterns = project["tool"]["setuptools"]["package-data"]["staylong"]

    assert "api/static/**/*" in patterns
