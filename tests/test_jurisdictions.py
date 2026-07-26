from doobielogic.jurisdictions import (
    JURISDICTION_NAMES,
    PROGRAM_SCOPES,
    compliance_context_text,
    get_jurisdiction_context,
    infer_jurisdiction_code,
    legal_jurisdiction_codes,
)


def test_registry_covers_states_dc_and_us_territories():
    assert len(JURISDICTION_NAMES) == 56
    assert {"DC", "AS", "GU", "MP", "PR", "VI"} <= set(JURISDICTION_NAMES)
    assert set(JURISDICTION_NAMES) == set(PROGRAM_SCOPES)


def test_every_jurisdiction_exposes_official_source_entry_points():
    for code in JURISDICTION_NAMES:
        context = get_jurisdiction_context(code)
        assert context is not None
        assert context.sources
        assert all(source.url.startswith("https://") for source in context.sources)
        assert context.rule_coverage == "official_source_registry_only"
        assert context.actionable is False
        assert context.last_updated


def test_compliance_context_is_fail_closed_about_exact_rules():
    text = compliance_context_text("CA")
    assert "Actionable without verification: no" in text
    assert "exact current rule text must still be verified" in text
    assert "Official sources:" in text


def test_missing_jurisdiction_is_low_confidence():
    text = compliance_context_text(None)
    assert "Confidence: low" in text
    assert "jurisdiction is required" in text.lower()


def test_legal_registry_includes_operating_territories_but_not_american_samoa():
    legal = set(legal_jurisdiction_codes())
    assert {"GU", "MP", "PR", "VI"} <= legal
    assert "AS" not in legal


def test_jurisdiction_is_inferred_only_when_user_names_it():
    assert infer_jurisdiction_code("What is the adult-use daily purchase limit in Massachusetts?") == "MA"
    assert infer_jurisdiction_code("What is the current rule in CA?") == "CA"
    assert infer_jurisdiction_code("What is the rule in Washington, D.C.?") == "DC"
    assert infer_jurisdiction_code("Is this allowed or should I ask compliance?") is None
