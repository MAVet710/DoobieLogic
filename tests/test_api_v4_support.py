from fastapi.testclient import TestClient

from doobielogic.api_v4 import app


client = TestClient(app)


def test_health_public():
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json()['status'] == 'ok'


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
