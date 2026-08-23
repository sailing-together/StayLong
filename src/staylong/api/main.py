"""Cloud Run runtime entry point for the StayLong API."""

import os

from staylong.api.app import create_app
from staylong.api.runtime import build_runtime_workflow


def _runtime_token() -> str:
    """Read the API token from the runtime environment without logging it."""
    token = os.environ.get("STAYLONG_API_TOKEN", "")
    if not token:
        raise RuntimeError("STAYLONG_API_TOKEN must be configured before starting the API")
    return token


app = create_app(api_token=_runtime_token(), workflow=build_runtime_workflow())
