from __future__ import annotations

from doobielogic.copilot import DoobieCopilot


def test_ask_with_buyer_brain_layers_explanation_for_buyer():
    copilot = DoobieCopilot()
    mapped = {
        "product": ["A", "B", "C"],
        "category": ["flower", "vapes", "edibles"],
        "brand": ["X", "X", "Y"],
        "price": [30, 40, 20],
        "quantity": [2, 0, 1],
        "inventory": [20, 15, 4],
        "revenue": [60, 0, 20],
    }

    res = copilot.ask_with_buyer_brain("find slow movers", mapped_data=mapped, persona="buyer", state="CA")
    assert res.mode == "inventory"
    assert "Role lens:" in res.explanation
    assert "File intelligence:" in res.explanation
    assert "Buyer brain" in res.explanation
    assert "Grounded source context:" in res.explanation
    assert isinstance(res.recommendations, list)


def test_ask_with_buyer_brain_non_buyer_stays_cautious():
    copilot = DoobieCopilot()
    mapped = {"quantity": [1, 2], "inventory": [10, 5]}
    res = copilot.ask_with_buyer_brain("ops check", mapped_data=mapped, persona="compliance", state="NY")
    assert "Buyer-specific recommendations are limited" in res.explanation
    assert res.mode == "ops"


def test_low_context_paths_return_low_confidence_and_lists():
    copilot = DoobieCopilot()
    res = copilot.ask_with_buyer_brain("quick check", mapped_data=None, persona="buyer", state="CA")
    assert res.confidence == "low"
    assert isinstance(res.risk_flags, list)
    assert isinstance(res.inefficiencies, list)
