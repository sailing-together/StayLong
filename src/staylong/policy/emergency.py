"""Deterministic routing for possible emergencies."""

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


def route_concern(message: str) -> str:
    """Classify configured red flags without medical assessment or side effects."""
    if any(term in message.casefold() for term in EMERGENCY_TERMS):
        return EMERGENCY_ROUTE
    return NORMAL_ROUTE
