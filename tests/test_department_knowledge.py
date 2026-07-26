from doobielogic.department_knowledge import get_department_knowledge, search_department_knowledge


def test_knowledge_available_and_searchable():
    entries = get_department_knowledge("cultivation")
    assert len(entries) >= 10
    matches = search_department_knowledge("cultivation", "microbial moisture room yield", limit=3)
    assert matches


def test_open_to_buy_question_returns_specific_buyer_guidance():
    matches = search_department_knowledge("buyer", "How should I manage open-to-buy?", limit=3)
    assert matches[0]["topic"] == "open-to-buy"
