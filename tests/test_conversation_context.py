from doobielogic.conversation_context import (
    build_conversation_profile,
    infer_state_from_history,
    jurisdiction_clarification_result,
    requires_jurisdiction,
)
from doobielogic.operational_answers import answer_operational_question


def test_jurisdiction_language_is_legally_material_without_forcing_a_mode():
    question = "What packaging and labeling controls should I verify in my jurisdiction?"
    assert requires_jurisdiction(question, "packaging") is True


def test_clarification_preserves_an_actionable_universal_baseline():
    question = "What packaging and labeling controls should I verify in my jurisdiction?"
    base = answer_operational_question(question, "packaging")
    result = jurisdiction_clarification_result(question, "Packaging", base)

    assert result["needs_clarification"] is True
    assert result["missing_context"] == ["jurisdiction", "license_type"]
    assert "Which U.S. state or territory" in result["answer"]
    assert "Universal operating baseline" in result["answer"]
    assert len(result["recommendations"]) >= 3


def test_history_restores_jurisdiction_and_license_context():
    history = [
        {"role": "user", "content": "I manage a New York dispensary."},
        {"role": "assistant", "content": "Understood."},
    ]
    assert infer_state_from_history(history) == "NY"
    profile = build_conversation_profile(
        "What label controls apply?",
        state=None,
        primary_mode="packaging",
        history=history,
    )
    assert profile["jurisdiction"] == "NY"
    assert profile["license_context"] == "retail dispensary"
