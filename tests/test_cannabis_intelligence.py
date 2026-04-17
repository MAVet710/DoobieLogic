from doobielogic.cannabis_intelligence import build_doobie_context, build_ai_input


def test_build_doobie_context_buyer_flags_low_doh():
    context = build_doobie_context(
        data={"days_on_hand": 10, "sell_through_rate": 0.25, "velocity": 3.4},
        mode="buyer",
    )

    assert context["mode"] == "buyer"
    assert context["inventory_summary"]["days_on_hand"] == 10
    assert any("restock risk" in flag.lower() for flag in context["risk_flags"])
    assert "buyer_doh_low" in context["relevant_rules"]


def test_build_ai_input_injects_structured_intel():
    ai_input = build_ai_input(
        question="What inventory is at risk?",
        data={"days_on_hand": 90, "sell_through_rate": 0.2},
        mode="buyer",
        state="CA",
    )

    assert ai_input["question"] == "What inventory is at risk?"
    assert "structured_context" in ai_input
    assert "intel_modules" in ai_input
    assert "buyer" in ai_input["intel_modules"]
    assert any("dead inventory risk" in flag.lower() for flag in ai_input["structured_context"]["risk_flags"])
