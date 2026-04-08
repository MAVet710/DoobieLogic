from doobielogic.department_knowledge import get_department_knowledge, search_department_knowledge


def test_knowledge_available_and_searchable():
    entries = get_department_knowledge("cultivation")
    assert len(entries) >= 10
    matches = search_department_knowledge("cultivation", "microbial moisture room yield", limit=3)
    assert matches
