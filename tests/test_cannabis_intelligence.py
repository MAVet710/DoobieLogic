from doobielogic.cannabis_intelligence import build_ai_input, build_doobie_context


def test_build_doobie_context_includes_required_fields():
    context = build_doobie_context(
        data={"days_on_hand": 10, "sell_through_rate": 0.25, "velocity": 3.4},
        mode="buyer",
        question="What inventory is risky?",
        state="CA",
    )

    assert context["mode"] == "buyer"
    assert "kpis" in context
    assert "file_insights" in context
    assert "risk_flags" in context
    assert "relevant_rules" in context
    assert "department_knowledge" in context
    assert "source_context" in context
    assert any("restock risk" in flag.lower() for flag in context["risk_flags"])


def test_build_ai_input_injects_structured_intel():
    ai_input = build_ai_input(
        question="What inventory is at risk?",
        data={"days_on_hand": 90, "sell_through_rate": 0.2},
        mode="inventory",
        state="CA",
    )

    assert ai_input["question"] == "What inventory is at risk?"
    assert "structured_context" in ai_input
    assert "intel_modules" in ai_input
    assert "buyer" in ai_input["intel_modules"]
    assert any("dead inventory risk" in flag.lower() for flag in ai_input["structured_context"]["risk_flags"])
