from fastapi.testclient import TestClient

from doobielogic.api_v4 import app
from doobielogic.key_management import KeyStore


client = TestClient(app)


def test_health_public():
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json()['status'] == 'ok'
    assert res.json()['license_validation_route'] == '/api/v1/license/validate'


def test_support_requires_auth_when_configured(monkeypatch):
    monkeypatch.setattr('doobielogic.api_v4.API_KEY', 'abc123')
    res = client.post('/api/v1/support/buyer_brief', json={'question': 'help', 'data': {}})
    assert res.status_code == 401


def test_support_response_format(monkeypatch):
    monkeypatch.setattr('doobielogic.api_v4.API_KEY', '')
    res = client.post('/api/v1/support/buyer_brief', json={'question': 'help', 'data': {'days_on_hand': 10}})
    assert res.status_code == 200
    payload = res.json()
    assert {
        "answer",
        "explanation",
        "recommendations",
        "confidence",
        "sources",
        "mode",
        "risk_flags",
        "inefficiencies",
        "routed_mode",
        "routed_by",
        "ai",
    } <= set(payload)
    assert payload["ai"]["provider"] in {"rules", "openai"}


def test_auth_check_uses_v4_service_auth(monkeypatch):
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "abc123")
    res = client.get("/api/v1/auth/check", headers={"x-api-key": "abc123"})
    assert res.status_code == 200
    assert res.json() == {
        "authenticated": True,
        "service": "DoobieLogic",
        "api_version": "v4",
    }


def test_module_curriculum_and_jurisdiction_registry_endpoints(monkeypatch):
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "")
    modules = client.get("/api/v1/knowledge/modules")
    jurisdictions = client.get("/api/v1/compliance/jurisdictions")

    assert modules.status_code == 200
    assert "cultivation" in modules.json()["modules"]
    assert modules.json()["modules"]["compliance"]["required_evidence"]
    assert jurisdictions.status_code == 200
    assert jurisdictions.json()["count"] == 56
    assert all(record["actionable"] is False for record in jurisdictions.json()["jurisdictions"])


def test_copilot_auto_routes_and_accepts_conversation_history(monkeypatch):
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "")
    res = client.post(
        "/api/v1/support/copilot",
        json={
            "question": "How should I review cultivation yield by room?",
            "state": "CA",
            "data": {"room": ["A"]},
            "history": [{"role": "user", "content": "We are reviewing last harvest."}],
        },
    )
    assert res.status_code == 200
    assert res.json()["routed_mode"] == "cultivation"
    assert res.json()["routed_by"] == "Detected from your question"


def test_compliance_question_without_jurisdiction_asks_a_natural_follow_up(monkeypatch):
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "")
    res = client.post(
        "/api/v1/support/copilot",
        json={"question": "whats the new daily limit for adult use purchases"},
    )
    payload = res.json()
    assert res.status_code == 200
    assert payload["routed_mode"] == "compliance"
    assert payload["needs_clarification"] is True
    assert payload["missing_context"] == ["jurisdiction"]
    assert "Which state or U.S. territory" in payload["answer"]


def test_compliance_question_infers_named_jurisdiction(monkeypatch):
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "")
    res = client.post(
        "/api/v1/support/copilot",
        json={"question": "What is the adult-use purchase limit in Massachusetts?"},
    )
    payload = res.json()
    assert res.status_code == 200
    assert payload["routed_mode"] == "compliance"
    assert payload["compliance_context"]["code"] == "MA"
    assert payload.get("needs_clarification") is not True
    assert "2 ounces" in payload["answer"]
    assert payload["rule_verified"] is True
    assert payload["rule_effective_date"] == "2026-04-19"


def test_compliance_follow_up_state_continues_previous_question(monkeypatch):
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "")
    res = client.post(
        "/api/v1/support/copilot",
        json={
            "question": "Massachusetts",
            "history": [
                {"role": "user", "content": "whats the new daily limit for adult use purchases"},
                {"role": "assistant", "content": "Which state or U.S. territory are you asking about?"},
            ],
        },
    )
    payload = res.json()
    assert res.status_code == 200
    assert payload["routed_mode"] == "compliance"
    assert payload["compliance_context"]["code"] == "MA"
    assert "2 ounces" in payload["answer"]
    assert payload["routed_by"] == "Continued from your previous compliance question"


def test_common_operational_question_returns_actionable_playbook(monkeypatch):
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "")
    res = client.post(
        "/api/v1/support/copilot",
        json={"question": "Our gummy potency varies across the batch. Give me a root-cause checklist."},
    )
    payload = res.json()
    assert res.status_code == 200
    assert payload["routed_mode"] == "kitchen"
    assert "Quarantine the batch" in payload["answer"]
    assert len(payload["recommendations"]) >= 3


def test_unverified_compliance_question_fails_usefully_with_official_sources(monkeypatch):
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "")
    res = client.post(
        "/api/v1/support/copilot",
        json={"question": "Can a dispensary transfer cannabis to another store in New Jersey?"},
    )
    payload = res.json()
    assert res.status_code == 200
    assert payload["routed_mode"] == "compliance"
    assert payload["rule_verified"] is False
    assert "will not guess" in payload["answer"]
    assert payload["sources"]


def test_id_queue_question_gets_operational_answer_without_inventing_a_rule(monkeypatch):
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "")
    res = client.post(
        "/api/v1/support/copilot",
        json={"question": "How can we reduce wait time while keeping ID verification compliant?"},
    )
    payload = res.json()
    assert res.status_code == 200
    assert payload["mode"] == "retail_ops"
    assert "arrival and ID verification" in payload["answer"]


def test_legacy_hyphenated_support_route_remains_compatible(monkeypatch):
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "")
    res = client.post(
        "/api/v1/support/inventory-check",
        json={"state": "MA", "data": {"days_on_hand": 8}},
    )
    assert res.status_code == 200
    assert res.json()["mode"] == "inventory"


def test_unknown_copilot_persona_routes_to_general_copilot(monkeypatch):
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "")
    res = client.post(
        "/api/v1/support/copilot",
        json={"question": "What should I focus on?", "persona": "legacy_unknown", "data": {}},
    )
    assert res.status_code == 200
    assert res.json()["mode"] == "copilot"


def test_extraction_support_accepts_single_record_scalar_values(monkeypatch):
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "")
    res = client.post(
        "/api/v1/support/copilot",
        json={
            "question": "How do I improve extraction yield?",
            "mode": "extraction",
            "state": "MA",
            "data": {"yield_pct": 0.45, "failed_batches": 1},
        },
    )
    assert res.status_code == 200
    assert res.json()["mode"] == "extraction"
    assert res.json()["answer"]


def test_validate_key_endpoint(monkeypatch, tmp_path):
    store = KeyStore(path=tmp_path / "keys.db")
    generated = store.create_api_key(
        company_name="Acme Cannabis",
        label="Buyer Dashboard",
        scope="buyer_dashboard",
        expiration_date=None,
        notes="",
    )
    monkeypatch.setattr('doobielogic.api_v4.KEY_STORE', store)
    monkeypatch.setattr('doobielogic.api_v4.KEY_VALIDATION_TOKEN', '')
    res = client.post('/api/v1/keys/validate', json={'api_key': generated.raw_key})
    assert res.status_code == 200
    payload = res.json()
    assert payload["valid"] is True
    assert payload["company"] == "Acme Cannabis"


def test_support_endpoint_accepts_authorization_bearer_with_generated_key(monkeypatch, tmp_path):
    store = KeyStore(path=tmp_path / "keys.db")
    generated = store.create_api_key(
        company_name="Acme Cannabis",
        label="Buyer Dashboard",
        scope="buyer_dashboard",
        expiration_date=None,
        notes="",
    )
    monkeypatch.setattr("doobielogic.api_v4.KEY_STORE", store)
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "")

    res = client.post(
        "/api/v1/support/buyer_brief",
        headers={"Authorization": f"Bearer {generated.raw_key}"},
        json={"question": "help", "data": {"days_on_hand": 10}},
    )
    assert res.status_code == 200


def test_health_reports_postgres_shared(monkeypatch):
    monkeypatch.setattr('doobielogic.api_v4.CONFIG', type('Cfg', (), {'diagnostics': lambda self: {
        'backend_mode': 'remote_api',
        'backend_mode_source': 'explicit',
        'preferred_backend_mode': 'postgres',
        'license_store_path': 'unused',
        'key_store_path': 'unused',
        'database_url_configured': True,
        'warnings': [],
        'production_like_env': True,
    }})())
    monkeypatch.setattr('doobielogic.api_v4.LICENSE_STORE', type('Lic', (), {'diagnostic': lambda self: {'backend': 'postgres', 'postgres_reachable': 'true'}})())
    monkeypatch.setattr('doobielogic.api_v4.KEY_STORE', type('Keys', (), {'diagnostic': lambda self: {'backend': 'postgres', 'postgres_reachable': 'true'}})())

    res = client.get('/health')
    payload = res.json()
    assert payload['postgres_configured'] == 'true'
    assert payload['postgres_reachable'] == 'true'
    assert payload['license_store_backend'] == 'postgres'
    assert payload['key_store_backend'] == 'postgres'
    assert payload['source_of_truth'] == 'postgres_shared'


def test_health_warns_when_local_mode_active(monkeypatch):
    monkeypatch.setattr('doobielogic.api_v4.CONFIG', type('Cfg', (), {'diagnostics': lambda self: {
        'backend_mode': 'local',
        'backend_mode_source': 'explicit',
        'preferred_backend_mode': 'local',
        'license_store_path': 'data/license_store.json',
        'key_store_path': 'data/key_store.db',
        'database_url_configured': False,
        'warnings': ['PRODUCTION_CONFIG_DRIFT_RISK_LOCAL_MODE_ACTIVE'],
        'production_like_env': True,
    }})())
    monkeypatch.setattr('doobielogic.api_v4.LICENSE_STORE', type('Lic', (), {'diagnostic': lambda self: {'backend': 'local_sqlite'}})())
    monkeypatch.setattr('doobielogic.api_v4.KEY_STORE', type('Keys', (), {'diagnostic': lambda self: {'backend': 'local_sqlite'}})())

    res = client.get('/health')
    assert 'Keys and licenses are deployment-local and may not survive redeploys.' in res.json()['warnings']


def test_health_reports_database_url_source(monkeypatch):
    monkeypatch.setattr('doobielogic.api_v4.CONFIG', type('Cfg', (), {'diagnostics': lambda self: {
        'backend_mode': 'local',
        'backend_mode_source': 'explicit',
        'preferred_backend_mode': 'local',
        'license_store_path': 'data/license_store.json',
        'key_store_path': 'data/key_store.db',
        'database_url_configured': True,
        'database_url_source': 'DOOBIE_DATABASE_URL',
        'warnings': [],
        'production_like_env': False,
    }})())
    monkeypatch.setattr('doobielogic.api_v4.LICENSE_STORE', type('Lic', (), {'diagnostic': lambda self: {'backend': 'postgres', 'postgres_reachable': 'true'}})())
    monkeypatch.setattr('doobielogic.api_v4.KEY_STORE', type('Keys', (), {'diagnostic': lambda self: {'backend': 'postgres', 'postgres_reachable': 'true'}})())

    res = client.get('/health')
    assert res.status_code == 200
    assert res.json()['database_url_source'] == 'DOOBIE_DATABASE_URL'


def test_admin_storage_diagnostics_counts_and_backends(monkeypatch):
    monkeypatch.setattr('doobielogic.api_v4.ADMIN_API_KEY', 'admin-secret')
    monkeypatch.setattr('doobielogic.api_v4.KEY_STORE', type('Keys', (), {
        'diagnostic': lambda self: {'backend': 'postgres'},
        'validate_admin_key': lambda self, token: {'valid': token == 'admin-secret'},
        'load_key_records': lambda self, key_type=None, key_role=None, search=None: (
            [{'is_active': True, 'is_revoked': False}, {'is_active': False, 'is_revoked': False}] if key_role == 'service' else [{'is_active': True, 'is_revoked': False}]
        ),
    })())
    monkeypatch.setattr('doobielogic.api_v4.LICENSE_STORE', type('Lic', (), {
        'diagnostic': lambda self: {'backend': 'postgres'},
        'list_licenses': lambda self: [type('L', (), {'status': 'active'})(), type('L', (), {'status': 'revoked'})()],
    })())

    res = client.get('/api/v1/admin/diagnostics/storage', headers={'Authorization': 'Bearer admin-secret'})
    payload = res.json()
    assert res.status_code == 200
    assert payload['source_of_truth'] == 'postgres_shared'
    assert payload['active_service_key_count'] == 1
    assert payload['active_admin_key_count'] == 1
    assert payload['active_license_count'] == 1
