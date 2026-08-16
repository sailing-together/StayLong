"""Command-line entry point for shared Terraform configuration validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from staylong.terraform_config import ConfigurationError, resolve_config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-root", type=Path, default=Path("infra/terraform/projects/config"))
    parser.add_argument("--project-config", required=True)
    parser.add_argument("--environment-config", required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    try:
        resolved = resolve_config(
            arguments.config_root,
            arguments.project_config,
            arguments.environment_config,
        )
    except ConfigurationError as error:
        raise SystemExit(str(error)) from error
    rendered = json.dumps(resolved, sort_keys=True, indent=2) + "\n"
    if arguments.output:
        arguments.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
