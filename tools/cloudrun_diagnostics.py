"""Produce a redacted, deterministic Cloud Run routing diagnostic summary."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def _conditions(resource: Mapping[str, Any]) -> dict[str, str]:
    conditions = resource.get("status", {}).get("conditions", [])
    return {
        item["type"]: item.get("status", item.get("state", "UNKNOWN"))
        for item in conditions
        if isinstance(item, Mapping) and isinstance(item.get("type"), str)
    }


def _urls(service: Mapping[str, Any]) -> list[str]:
    value = service.get("metadata", {}).get("annotations", {}).get("run.googleapis.com/urls", "[]")
    if not isinstance(value, str):
        return []
    try:
        urls = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [url for url in urls if isinstance(url, str)]


def _invokers(policy: Mapping[str, Any]) -> list[str]:
    principals: set[str] = set()
    for binding in policy.get("bindings", []):
        if not isinstance(binding, Mapping) or binding.get("role") != "roles/run.invoker":
            continue
        members = binding.get("members", [])
        if isinstance(members, Sequence) and not isinstance(members, str):
            principals.update(member for member in members if isinstance(member, str))
    return sorted(principals)


def build_summary(
    service: Mapping[str, Any], revision: Mapping[str, Any], policy: Mapping[str, Any]
) -> dict[str, object]:
    """Summarise routing state without printing tokens, secrets, or request bodies."""
    service_conditions = _conditions(service)
    revision_conditions = _conditions(revision)
    traffic = service.get("status", {}).get("traffic", [])
    traffic_summary = [
        {"revision": item.get("revisionName"), "percent": item.get("percent")}
        for item in traffic
        if isinstance(item, Mapping)
    ]
    invokers = _invokers(policy)
    annotations = service.get("metadata", {}).get("annotations", {})
    return {
        "service": {
            "ingress": annotations.get("run.googleapis.com/ingress"),
            "latest_ready_revision": service.get("status", {}).get("latestReadyRevisionName"),
            "ready": service_conditions.get("Ready", "UNKNOWN"),
            "routes_ready": service_conditions.get("RoutesReady", "UNKNOWN"),
            "traffic": traffic_summary,
            "urls": _urls(service),
        },
        "revision": {
            "container_healthy": revision_conditions.get("ContainerHealthy", "UNKNOWN"),
            "name": revision.get("metadata", {}).get("name"),
            "ready": revision_conditions.get("Ready", "UNKNOWN"),
        },
        "invoker_policy": {"public": "allUsers" in invokers, "principals": invokers},
    }


def _read_json(path: str) -> Mapping[str, Any]:
    value = json.loads(Path(path).read_text())
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service-json", required=True)
    parser.add_argument("--revision-json", required=True)
    parser.add_argument("--policy-json", required=True)
    args = parser.parse_args()
    summary = build_summary(
        _read_json(args.service_json),
        _read_json(args.revision_json),
        _read_json(args.policy_json),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
