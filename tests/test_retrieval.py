from doobielogic.retrieval import build_retrieval_context


def test_retrieval_returns_current_curated_record_and_official_sources():
    context = build_retrieval_context(
        "What packaging and labeling controls apply in New York?",
        state="NY",
        primary_mode="packaging",
        secondary_modes=["compliance"],
    )
    assert context["status"] == "curated_evidence_match"
    assert any(record["record_id"] == "ny_plma_2025" for record in context["curated_records"])
    assert all(record["evidence_scope"] == "summary_only" for record in context["curated_records"])
    assert context["verified_rule_available"] is False
    assert "do not prove unstated rule details" in context["warning"]
    assert "https://cannabis.ny.gov/plma" in context["source_urls"]
    assert context["jurisdiction"]["code"] == "NY"


def test_registry_only_is_not_mislabeled_as_verified_rule():
    context = build_retrieval_context(
        "What exact label font size applies?",
        state="AK",
        primary_mode="packaging",
        secondary_modes=["compliance"],
    )
    assert context["verified_rule_available"] is False
    assert context["status"] == "official_registry_only"
    assert context["warning"]

