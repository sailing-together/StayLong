import json
import shutil
from pathlib import Path

import pytest

from staylong.terraform_config import ConfigurationError, resolve_config

CONFIG_ROOT = Path("infra/terraform/projects/config")


def test_resolve_config_merges_common_environment_and_project_deterministically() -> None:
    config = resolve_config(CONFIG_ROOT, "staylong.json", "sandbox.json")

    assert config["project_id"] == "staylong"
    assert config["region"] == "australia-southeast2"
    assert config["artifact_registry_repository_id"] == "staylong"
    assert config["cloudbuild_staging_bucket_name"] == "staylong-cloudbuild-186136682416"
    assert config["labels"] == {"environment": "sandbox", "product": "staylong"}


def test_resolve_config_rejects_unknown_selection_name() -> None:
    with pytest.raises(ConfigurationError, match="Unknown project configuration"):
        resolve_config(CONFIG_ROOT, "other-project.json", "sandbox.json")


def test_public_sandbox_config_includes_non_secret_public_edge_contract() -> None:
    config = resolve_config(
        CONFIG_ROOT,
        "staylong-public-sandbox.json",
        "stay-long-sydney-sandbox.json",
    )

    assert config["public_domain"] == "staylonghome.com"
    assert config["www_public_domain"] == "www.staylonghome.com"
    assert config["public_edge_lockdown_enabled"] is False
    assert len(config["cloudflare_zone_id"]) == 32


def test_resolve_config_rejects_secret_like_keys(tmp_path: Path) -> None:
    copied_root = tmp_path / "config"
    shutil.copytree(CONFIG_ROOT, copied_root)
    environment_path = copied_root / "sandbox.json"
    environment = json.loads(environment_path.read_text(encoding="utf-8"))
    environment["api_token"] = "not-allowed"
    environment_path.write_text(json.dumps(environment))

    with pytest.raises(ConfigurationError, match="secret-like"):
        resolve_config(copied_root, "staylong.json", "sandbox.json")


def test_public_edge_config_rejects_cloudflare_api_token(tmp_path: Path) -> None:
    copied_root = tmp_path / "config"
    shutil.copytree(CONFIG_ROOT, copied_root)
    project_path = copied_root / "staylong-public-sandbox.json"
    project = json.loads(project_path.read_text(encoding="utf-8"))
    project["cloudflare_api_token"] = "must-not-be-checked-in"
    project_path.write_text(json.dumps(project))

    with pytest.raises(ConfigurationError, match="secret-like"):
        resolve_config(
            copied_root,
            "staylong-public-sandbox.json",
            "stay-long-sydney-sandbox.json",
        )
