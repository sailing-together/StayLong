"""Contract tests for the bounded, structured intake agent."""

import pytest


class StaticProvider:
    """A local model adapter that returns a recorded structured response."""

    def __init__(self, response: object) -> None:
        self.response = response
        self.requests: list[tuple[str, str]] = []

    def generate_json(self, *, system_instruction: str, prompt: str) -> object:
        self.requests.append((system_instruction, prompt))
        return self.response


def test_intake_returns_the_validated_prompt_contract_structure() -> None:
    from staylong.agents.intake import IntakeAgent

    provider = StaticProvider(
        {
            "plain_language_summary": "The shower step is difficult to manage.",
            "home_area": "bathroom",
            "reported_difficulty": "Stepping into the shower is harder than before.",
            "missing_facts": ["Whether there is a support person available."],
            "assessment_preparation_topics": ["Describe the shower entry and usual routine."],
            "proposed_next_step": "prepare_assessment_pack",
        }
    )

    result = IntakeAgent(provider=provider).intake(
        "Mum says stepping into the shower has become difficult."
    )

    assert result.plain_language_summary == "The shower step is difficult to manage."
    assert result.home_area == "bathroom"
    assert result.reported_difficulty == "Stepping into the shower is harder than before."
    assert result.missing_facts == ("Whether there is a support person available.",)
    assert result.assessment_preparation_topics == (
        "Describe the shower entry and usual routine.",
    )
    assert result.proposed_next_step == "prepare_assessment_pack"
    assert len(provider.requests) == 1


def test_intake_rejects_a_model_response_outside_the_schema() -> None:
    from staylong.agents.intake import IntakeAgent, IntakeSchemaError

    provider = StaticProvider(
        {
            "plain_language_summary": "A summary",
            "home_area": "garage",
            "reported_difficulty": "A difficulty",
            "missing_facts": [],
            "assessment_preparation_topics": [],
            "proposed_next_step": "book_a_provider",
        }
    )

    with pytest.raises(IntakeSchemaError):
        IntakeAgent(provider=provider).intake("The garage step is hard to use.")


def test_intake_uses_deterministic_emergency_routing_without_calling_the_model() -> None:
    from staylong.agents.intake import EmergencyRouteRequired, IntakeAgent

    provider = StaticProvider({})

    with pytest.raises(EmergencyRouteRequired, match=r"Triple Zero \(000\)"):
        IntakeAgent(provider=provider).intake("My parent is unconscious. Should I wait?")

    assert provider.requests == []
