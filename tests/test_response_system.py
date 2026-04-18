from __future__ import annotations

from doobielogic.response_system import (
    RESPONSE_BUILDERS,
    RESPONSE_MODE_CONFIG,
    build_buyer_response,
    build_extraction_response,
    infer_confidence,
)


REQUIRED_KEYS = {
    "answer",
    "explanation",
    "recommendations",
    "confidence",
    "sources",
    "mode",
    "risk_flags",
    "inefficiencies",
}


def _sample_kwargs() -> dict:
    return {
        "quick_answer": "Immediate action required.",
        "explanation_context": "Sample cannabis operations context.",
        "recommendations": ["Take action."],
        "risk_flags": ["risk"],
        "inefficiencies": ["inefficiency"],
        "confidence": "medium",
        "sources": ["source"],
    }


def test_each_mode_builder_returns_standard_shape():
    kwargs = _sample_kwargs()
    for mode, builder in RESPONSE_BUILDERS.items():
        response = builder(**kwargs).to_dict()
        assert set(response.keys()) == REQUIRED_KEYS
        assert response["mode"] == mode


def test_buyer_and_extraction_mode_have_distinct_focus_text():
    kwargs = _sample_kwargs()
    buyer = build_buyer_response(**kwargs)
    extraction = build_extraction_response(**kwargs)
    assert "assortment gaps" in buyer.explanation
    assert "yield" in extraction.explanation


def test_infer_confidence_low_when_context_is_weak():
    confidence = infer_confidence(
        has_structured_data=False,
        has_grounding=False,
        has_relevant_rules=False,
        weak_context=True,
    )
    assert confidence == "low"


def test_missing_risk_flags_and_inefficiencies_are_safe_lists():
    response = build_buyer_response(
        quick_answer="Answer",
        explanation_context="Context",
        recommendations=["Do thing"],
        risk_flags=None,
        inefficiencies=None,
        confidence="medium",
        sources=[],
    )
    payload = response.to_dict()
    assert payload["risk_flags"] == []
    assert payload["inefficiencies"] == []


def test_mode_config_supports_expected_modes():
    expected = {"buyer", "inventory", "extraction", "ops", "copilot", "compliance", "executive"}
    assert expected.issubset(RESPONSE_MODE_CONFIG.keys())
