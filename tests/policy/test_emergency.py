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
