from doobielogic.conversational_ai import build_conversation_instructions
from doobielogic.professional_domains import (
    PROFESSIONAL_DOMAINS,
    professional_domain_catalog,
    professional_domain_result,
)


def test_professional_domain_catalog_covers_cross_functional_cannabis_business():
    assert set(PROFESSIONAL_DOMAINS) == {
        "quality",
        "laboratory",
        "distribution",
        "security",
        "finance",
        "people",
        "maintenance",
        "marketing",
        "product_development",
        "ehs",
    }
    assert all(domain.key_metrics for domain in PROFESSIONAL_DOMAINS.values())
    assert all(domain.required_evidence for domain in PROFESSIONAL_DOMAINS.values())
    assert all(domain.safety_boundary for domain in PROFESSIONAL_DOMAINS.values())


def test_professional_domain_fallback_is_useful_and_evidence_bounded():
    result = professional_domain_result("How should we improve this?", "finance")
    assert result is not None
    assert result["mode"] == "finance"
    assert len(result["recommendations"]) == 3
    assert result["risk_flags"]
    assert result["sources"] == ["[professional_domain:finance]"]


def test_conversation_instructions_include_specialist_domain_knowledge():
    instructions = build_conversation_instructions("security")
    assert "Professional domain: Security & Data Protection" in instructions
    assert "Required evidence:" in instructions
    assert "Safety boundary:" in instructions


def test_catalog_is_json_ready():
    catalog = professional_domain_catalog()
    assert catalog["maintenance"]["mode"] == "maintenance"
    assert catalog["marketing"]["decision_rules"]
