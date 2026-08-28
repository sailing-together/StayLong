"""Resolve the API token used by the serving process."""

import secrets
from collections.abc import Mapping


def runtime_token(environment: Mapping[str, str]) -> str:
    """Return the configured token, or an ephemeral token for public sandbox only."""
    token = environment.get("STAYLONG_API_TOKEN", "").strip()
    if token:
        return token
    if environment.get("STAYLONG_PUBLIC_SANDBOX", "").casefold() == "true":
        return secrets.token_urlsafe(32)
    raise RuntimeError("STAYLONG_API_TOKEN must be configured before starting the API")
