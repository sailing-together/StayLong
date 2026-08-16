"""Tests for deterministic emergency routing."""

from inspect import signature

import pytest

from staylong.policy.emergency import EMERGENCY_TERMS, route_concern


@pytest.mark.parametrize(
    "term",
    sorted(EMERGENCY_TERMS),
)
def test_configured_emergency_terms_route_to_emergency(term: str) -> None:
    assert route_concern(f"Please help: {term}.") == "emergency_route"


@pytest.mark.parametrize(
    "message",
    [
        "Could you help coordinate a grocery delivery next week?",
        "Mum would like a handrail installed.",
        "",
    ],
)
def test_non_emergency_concerns_route_normally(message: str) -> None:
    assert route_concern(message) == "normal_route"


def test_router_accepts_only_the_message_and_exposes_no_callback_boundary() -> None:
    assert tuple(signature(route_concern).parameters) == ("message",)


def test_emergency_concern_has_a_user_visible_triple_zero_response() -> None:
    from staylong.policy.emergency import emergency_response

    response = emergency_response("My parent is unconscious.")

    assert response is not None
    assert response.call_number == "000"
    assert response.heading == "Call Triple Zero (000) now"
    assert "cannot assess" in response.message


def test_non_emergency_concern_has_no_emergency_response() -> None:
    from staylong.policy.emergency import emergency_response

    assert emergency_response("Mum would like a handrail installed.") is None
