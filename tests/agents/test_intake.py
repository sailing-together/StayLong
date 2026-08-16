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
            "missing_facts": [
                {
                    "key": "support_contacts",
                    "question": "Who is authorised to help coordinate this?",
                    "reason": "StayLong only coordinates with authorised contacts.",
                }
            ],
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
    assert result.missing_facts[0].key == "support_contacts"
    assert result.missing_facts[0].question == "Who is authorised to help coordinate this?"
    assert result.assessment_preparation_topics == (
        "Describe the shower entry and usual routine.",
    )
    assert result.proposed_next_step == "prepare_assessment_pack"
    assert len(provider.requests) == 1


def test_intake_generates_a_non_clinical_assessment_preparation_pack() -> None:
    """The pack makes missing household facts usable without inferring eligibility."""
    from staylong.agents.intake import IntakeAgent

    provider = StaticProvider(
        {
            "plain_language_summary": "The shower entry is difficult to manage.",
            "home_area": "bathroom",
            "reported_difficulty": "Stepping into the shower has become difficult.",
            "missing_facts": [
                {
                    "key": "assessment_status",
                    "question": "Has a My Aged Care assessment already been arranged?",
                    "reason": "This helps the family prepare the appropriate next step.",
                },
                {
                    "key": "housing_tenure",
                    "question": "Is the home owned or rented?",
                    "reason": "Permission requirements may affect planning.",
                },
            ],
            "assessment_preparation_topics": [
                "Describe the shower entry and usual bathroom routine.",
                "Bring any relevant assessment correspondence.",
            ],
            "proposed_next_step": "prepare_assessment_pack",
        }
    )

    pack = IntakeAgent(provider=provider).prepare_assessment_pack(
        "Mum says stepping into the shower has become difficult."
    )

    assert pack.concern_summary == "The shower entry is difficult to manage."
    assert pack.information_to_confirm[0].key == "assessment_status"
    assert pack.assessment_discussion_topics == (
        "Describe the shower entry and usual bathroom routine.",
        "Bring any relevant assessment correspondence.",
    )
    assert pack.official_pathways == ("https://www.myagedcare.gov.au/",)
    assert "does not determine eligibility" in pack.boundary_note
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


def test_intake_rejects_a_missing_fact_outside_the_non_clinical_contract() -> None:
    """The model cannot introduce clinical questions into a household fact checklist."""
    from staylong.agents.intake import IntakeAgent, IntakeSchemaError

    provider = StaticProvider(
        {
            "plain_language_summary": "A summary",
            "home_area": "bathroom",
            "reported_difficulty": "A difficulty",
            "missing_facts": [
                {
                    "key": "medical_diagnosis",
                    "question": "What is the diagnosis?",
                    "reason": "This is not a household fact.",
                }
            ],
            "assessment_preparation_topics": [],
            "proposed_next_step": "prepare_assessment_pack",
        }
    )

    with pytest.raises(IntakeSchemaError, match="missing_facts key"):
        IntakeAgent(provider=provider).intake("The shower step is hard to use.")


def test_intake_uses_deterministic_emergency_routing_without_calling_the_model() -> None:
    from staylong.agents.intake import EmergencyRouteRequired, IntakeAgent

    provider = StaticProvider({})

    with pytest.raises(EmergencyRouteRequired, match=r"Triple Zero \(000\)"):
        IntakeAgent(provider=provider).intake("My parent is unconscious. Should I wait?")

    assert provider.requests == []


@pytest.mark.parametrize(
    "medical_question",
    [
        "Should I wait before getting help for this medical problem?",
        "Can you tell me whether this is medically safe?",
    ],
)
def test_intake_refuses_medical_triage_without_calling_the_model(medical_question: str) -> None:
    from staylong.agents.intake import IntakeAgent, MedicalTriageRefusalRequired

    provider = StaticProvider({})

    with pytest.raises(MedicalTriageRefusalRequired, match="cannot provide medical triage"):
        IntakeAgent(provider=provider).intake(medical_question)

    assert provider.requests == []
