from __future__ import annotations

from doobielogic.copilot import DoobieCopilot


def test_ask_with_buyer_brain_layers_answer_for_buyer():
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
    assert "Role lens:" in res.answer
    assert "File intelligence:" in res.answer
    assert "Buyer brain" in res.answer
    assert "Grounded source context:" in res.answer


def test_ask_with_buyer_brain_non_buyer_stays_cautious():
    copilot = DoobieCopilot()
    mapped = {"quantity": [1, 2], "inventory": [10, 5]}
    res = copilot.ask_with_buyer_brain("ops check", mapped_data=mapped, persona="compliance", state="NY")
    assert "Department-specific operational analysis is preferred" in res.answer
