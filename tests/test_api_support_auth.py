from fastapi.testclient import TestClient

import doobielogic.api as api_module


client = TestClient(api_module.app)


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_missing_api_key_returns_401(monkeypatch):
    monkeypatch.setattr(api_module, "API_KEY", "secret123")
    res = client.get("/states")
    assert res.status_code == 401


def test_valid_api_key_returns_success(monkeypatch):
    monkeypatch.setattr(api_module, "API_KEY", "secret123")
    res = client.get("/states", headers=_auth_header("secret123"))
    assert res.status_code == 200


def test_auth_check_endpoint(monkeypatch):
    monkeypatch.setattr(api_module, "API_KEY", "secret123")
    res = client.get("/api/v1/auth/check", headers=_auth_header("secret123"))
    assert res.status_code == 200
    assert res.json() == {"authenticated": True, "service": "DoobieLogic"}


def test_support_endpoint_standard_shape(monkeypatch):
    monkeypatch.setattr(api_module, "API_KEY", "secret123")
    res = client.post(
        "/api/v1/support/buyer_brief",
        json={"question": "What should I do?", "state": "CA", "data": {"days_on_hand": 10}},
        headers=_auth_header("secret123"),
    )
    assert res.status_code == 200
    payload = res.json()
    assert set(payload.keys()) == {"answer", "explanation", "recommendations", "confidence", "sources", "mode"}
