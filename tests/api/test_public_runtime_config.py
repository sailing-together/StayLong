"""Public sandbox runtime wiring contracts."""

from datetime import timedelta

from staylong.api.runtime import build_public_sandbox_config


def test_public_sandbox_config_uses_secret_and_durable_case_access() -> None:
    config = build_public_sandbox_config(
        {"STAYLONG_PUBLIC_SANDBOX": "true", "STAYLONG_PUBLIC_SESSION_SECRET": "session-secret"},
        firestore_client=object(),
    )

    assert config is not None
    assert config.session_secret == "session-secret"
    assert config.session_lifetime == timedelta(hours=24)
    assert config.cookie_secure is True


def test_private_runtime_does_not_enable_public_sandbox_routes() -> None:
    assert build_public_sandbox_config({}, firestore_client=object()) is None
