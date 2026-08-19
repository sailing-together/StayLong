"""Tests for redacted Cloud Run diagnostic summaries."""

from tools.cloudrun_diagnostics import build_summary


def test_summary_surfaces_route_readiness_and_public_invoker_state() -> None:
    summary = build_summary(
        {
            "metadata": {
                "annotations": {
                    "run.googleapis.com/ingress": "all",
                    "run.googleapis.com/urls": '["https://canonical.run.app", "https://hash.a.run.app"]',
                }
            },
            "status": {
                "latestReadyRevisionName": "staylong-sydney-00004",
                "traffic": [{"revisionName": "staylong-sydney-00004", "percent": 100}],
                "conditions": [
                    {"type": "Ready", "state": "CONDITION_SUCCEEDED"},
                    {"type": "RoutesReady", "state": "CONDITION_SUCCEEDED"},
                ],
            },
        },
        {
            "metadata": {"name": "staylong-sydney-00004"},
            "status": {
                "conditions": [
                    {"type": "Ready", "state": "CONDITION_SUCCEEDED"},
                    {"type": "ContainerHealthy", "state": "CONDITION_SUCCEEDED"},
                ]
            },
        },
        {
            "bindings": [
                {
                    "role": "roles/run.invoker",
                    "members": [
                        "serviceAccount:staylong-app-deployer@staylong.iam.gserviceaccount.com"
                    ],
                }
            ]
        },
    )

    assert summary["service"] == {
        "ingress": "all",
        "latest_ready_revision": "staylong-sydney-00004",
        "ready": "CONDITION_SUCCEEDED",
        "routes_ready": "CONDITION_SUCCEEDED",
        "traffic": [{"percent": 100, "revision": "staylong-sydney-00004"}],
        "urls": ["https://canonical.run.app", "https://hash.a.run.app"],
    }
    assert summary["revision"] == {
        "container_healthy": "CONDITION_SUCCEEDED",
        "name": "staylong-sydney-00004",
        "ready": "CONDITION_SUCCEEDED",
    }
    assert summary["invoker_policy"] == {
        "public": False,
        "principals": ["serviceAccount:staylong-app-deployer@staylong.iam.gserviceaccount.com"],
    }
