from __future__ import annotations

from fastapi.testclient import TestClient

from doobielogic.api_v4 import app
from doobielogic.license_store import LicenseStore


client = TestClient(app)


def test_admin_endpoints_require_admin_bearer(monkeypatch, tmp_path):
    monkeypatch.setattr("doobielogic.api_v4.ADMIN_API_KEY", "admin-secret")
    monkeypatch.setattr("doobielogic.api_v4.LICENSE_STORE", LicenseStore(path=tmp_path / "store.json"))

    no_auth = client.get("/api/v1/admin/customers")
    assert no_auth.status_code == 401

    good = client.get("/api/v1/admin/customers", headers={"Authorization": "Bearer admin-secret"})
    assert good.status_code == 200
    assert good.json() == {"customers": []}


def test_end_to_end_admin_and_validation_flow(monkeypatch, tmp_path):
    monkeypatch.setattr("doobielogic.api_v4.ADMIN_API_KEY", "admin-secret")
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "service-key")
    monkeypatch.setattr("doobielogic.api_v4.LICENSE_STORE", LicenseStore(path=tmp_path / "store.json"))

    admin_headers = {"Authorization": "Bearer admin-secret"}

    customer = client.post(
        "/api/v1/admin/customers",
        headers=admin_headers,
        json={
            "company_name": "Acme Cannabis",
            "contact_name": "Pat",
            "contact_email": "pat@example.com",
            "notes": "first customer",
        },
    )
    assert customer.status_code == 200
    customer_id = customer.json()["customer_id"]

    generated = client.post(
        "/api/v1/admin/licenses/generate",
        headers=admin_headers,
        json={"customer_id": customer_id, "plan_type": "premium"},
    )
    assert generated.status_code == 200
    license_key = generated.json()["license_key"]

    valid = client.post(
        "/api/v1/license/validate",
        headers={"x-api-key": "service-key"},
        json={"license_key": license_key},
    )
    assert valid.status_code == 200
    assert valid.json()["valid"] is True
    assert valid.json()["plan_type"] == "premium"

    revoked = client.post(
        "/api/v1/admin/licenses/revoke",
        headers=admin_headers,
        json={"license_key": license_key, "revoked_reason": "non-payment"},
    )
    assert revoked.status_code == 200

    invalid = client.post(
        "/api/v1/license/validate",
        headers={"x-api-key": "service-key"},
        json={"license_key": license_key},
    )
    assert invalid.status_code == 200
    assert invalid.json() == {"valid": False, "reason": "revoked"}
