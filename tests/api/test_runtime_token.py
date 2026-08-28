"""Runtime API token startup contracts."""

from staylong.api.runtime_token import runtime_token


def test_public_sandbox_generates_an_internal_token_without_private_secret() -> None:
    token = runtime_token({"STAYLONG_PUBLIC_SANDBOX": "true"})

    assert len(token) >= 32


def test_private_runtime_requires_configured_api_token() -> None:
    try:
        runtime_token({})
    except RuntimeError as error:
        assert str(error) == "STAYLONG_API_TOKEN must be configured before starting the API"
    else:
        raise AssertionError("private runtime must reject a missing API token")
