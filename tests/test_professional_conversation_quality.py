from fastapi.testclient import TestClient

from doobielogic.api_v4 import app


client = TestClient(app)


def _ask(monkeypatch, question: str, state: str | None = None) -> dict:
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "")
    body = {"question": question}
    if state:
        body["state"] = state
    response = client.post("/api/v1/support/copilot", json=body)
    assert response.status_code == 200
    return response.json()


def test_cultivation_mildew_response_prioritizes_containment(monkeypatch):
    payload = _ask(
        monkeypatch,
        "My flower room has rising humidity and powdery mildew pressure. What should I do today?",
        "CA",
    )
    assert payload["routed_mode"] == "cultivation"
    assert "Contain the affected room today" in payload["answer"]
    assert "unapproved pesticide" in " ".join(payload["risk_flags"])
    assert len(payload["recommendations"]) >= 4


def test_gummy_potency_uses_manufacturing_investigation(monkeypatch):
    payload = _ask(monkeypatch, "Our gummy potency is uneven across the batch. What should we quarantine and test?", "NY")
    assert payload["routed_mode"] == "kitchen"
    assert "Quarantine the batch" in payload["answer"]
    assert "mixer/depositor position" in " ".join(payload["recommendations"])


def test_released_product_contamination_uses_recall_containment(monkeypatch):
    payload = _ask(
        monkeypatch,
        "A customer complaint suggests contamination in a released edible lot. Walk me through containment.",
        "WA",
    )
    assert payload["routed_mode"] == "quality"
    assert "Contain the affected lots first" in payload["answer"]
    assert "distribution" in payload["answer"]


def test_manifest_mismatch_explicitly_stops_transfer(monkeypatch):
    payload = _ask(monkeypatch, "A delivery manifest does not match the physical shipment. Can the driver continue?", "NJ")
    assert payload["routed_mode"] == "distribution"
    assert "Do not continue the transfer" in payload["answer"]
    assert "Do not edit records" in " ".join(payload["risk_flags"])


def test_cash_pressure_routes_to_finance_and_protects_critical_cash(monkeypatch):
    payload = _ask(monkeypatch, "Cash is tight and inventory is aging. What actions should the GM take this week?", "NV")
    assert payload["routed_mode"] == "finance"
    assert "Protect the next 13 weeks" in payload["answer"]
    assert "Freeze speculative buys" in payload["answer"]
    assert len(payload["recommendations"]) >= 4


def test_ransomware_response_preserves_evidence_and_traceability(monkeypatch):
    payload = _ask(
        monkeypatch,
        "We may have a ransomware incident affecting seed-to-sale terminals. What do we do now?",
        "IL",
    )
    assert payload["routed_mode"] == "security"
    assert "preserve evidence" in payload["answer"]
    assert "traceability continuity" in payload["answer"]


def test_oos_response_forbids_testing_into_compliance(monkeypatch):
    payload = _ask(monkeypatch, "The lab reported an OOS result. Can we retest until it passes?", "OR")
    assert payload["routed_mode"] == "laboratory"
    assert "Preserve raw data" in payload["answer"]
    assert "repeat testing until a passing result" in " ".join(payload["risk_flags"])


def test_known_state_purchase_limit_is_specific_and_sourced(monkeypatch):
    payload = _ask(monkeypatch, "What is the adult-use daily purchase limit in Massachusetts?")
    assert payload["routed_mode"] == "compliance"
    assert payload["rule_verified"] is True
    assert "2 ounces" in payload["answer"]
    assert payload["sources"]


def test_unknown_exact_rule_does_not_invent_an_answer(monkeypatch):
    payload = _ask(monkeypatch, "Can a dispensary transfer cannabis to another store in New Jersey?")
    assert payload["routed_mode"] == "compliance"
    assert payload["rule_verified"] is False
    assert "will not guess" in payload["answer"]
    assert payload["sources"]
