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
    assert set(payload.keys()) == {'answer', 'explanation', 'recommendations', 'confidence', 'sources', 'mode', 'risk_flags', 'inefficiencies'}


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
        'database_url_source': 'DATABASE_URL',
        'warnings': [],
        'production_like_env': True,
    }})())
    monkeypatch.setattr('doobielogic.api_v4.LICENSE_STORE', type('Lic', (), {'diagnostic': lambda self: {'backend': 'postgres', 'postgres_reachable': 'true'}})())
    monkeypatch.setattr('doobielogic.api_v4.KEY_STORE', type('Keys', (), {'diagnostic': lambda self: {'backend': 'postgres', 'postgres_reachable': 'true'}})())

    res = client.get('/health')
    payload = res.json()
    assert payload['postgres_configured'] == 'true'
    assert payload['postgres_config_source'] == 'DATABASE_URL'
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
