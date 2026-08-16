"""Deterministic routing and user-visible response for possible emergencies."""

from dataclasses import dataclass

EMERGENCY_ROUTE = "emergency_route"
NORMAL_ROUTE = "normal_route"
EMERGENCY_TERMS = frozenset(
    {
        "call 000",
        "triple zero",
        "unconscious",
        "not breathing",
    }
)
MEDICAL_TRIAGE_TERMS = frozenset(
    {
        "medically safe",
        "should i see a doctor",
        "should i wait",
        "what medical care",
    }
)


@dataclass(frozen=True, slots=True)
class EmergencyResponse:
    """A non-clinical, immediate emergency instruction for the user interface."""

    call_number: str
    heading: str
    message: str


def route_concern(message: str) -> str:
    """Classify configured red flags without medical assessment or side effects."""
    if any(term in message.casefold() for term in EMERGENCY_TERMS):
        return EMERGENCY_ROUTE
    return NORMAL_ROUTE


def requires_medical_triage_refusal(message: str) -> bool:
    """Identify direct medical-triage requests that must not reach a model."""
    return any(term in message.casefold() for term in MEDICAL_TRIAGE_TERMS)


def emergency_response(message: str) -> EmergencyResponse | None:
    """Return the immediate Triple Zero response when deterministic policy matches."""
    if route_concern(message) != EMERGENCY_ROUTE:
        return None
    return EmergencyResponse(
        call_number="000",
        heading="Call Triple Zero (000) now",
        message=(
            "StayLong cannot assess this situation. For an emergency in Australia, "
            "call Triple Zero (000) now."
        ),
    )
