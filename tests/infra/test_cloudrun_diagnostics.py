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
                    {"type": "Ready", "status": "True"},
                    {"type": "RoutesReady", "status": "True"},
                ],
            },
        },
        {
            "metadata": {"name": "staylong-sydney-00004"},
            "status": {
                "conditions": [
                    {"type": "Ready", "status": "True"},
                    {"type": "ContainerHealthy", "status": "True"},
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
        "ready": "True",
        "routes_ready": "True",
        "traffic": [{"percent": 100, "revision": "staylong-sydney-00004"}],
        "urls": ["https://canonical.run.app", "https://hash.a.run.app"],
    }
    assert summary["revision"] == {
        "container_healthy": "True",
        "name": "staylong-sydney-00004",
        "ready": "True",
    }
    assert summary["invoker_policy"] == {
        "public": False,
        "principals": ["serviceAccount:staylong-app-deployer@staylong.iam.gserviceaccount.com"],
    }
