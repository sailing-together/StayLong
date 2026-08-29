"""Contract for isolating the rebuilt sandbox in its own GCP project."""

import json
from pathlib import Path

CONFIG_ROOT = Path("infra/terraform/projects/config")


def test_stay_long_sydney_v2_config_uses_the_rebuilt_project_and_unique_state() -> None:
    project_text = (CONFIG_ROOT / "stay-long-sydney-v2.json").read_text(encoding="utf-8")
    env_text = (CONFIG_ROOT / "stay-long-sydney-sandbox.json").read_text(encoding="utf-8")
    project = json.loads(project_text)
    environment = json.loads(env_text)

    assert project["project"] == "stay-long-sydney-v2"
    assert environment["project_id"] == "stay-long"
    assert environment["region"] == "australia-southeast1"
    assert environment["state_bucket_name"] == "stay-long-terraform-state-864199179076"
    assert project["cloudbuild_staging_bucket_name"] == "stay-long-cloudbuild-864199179076"
