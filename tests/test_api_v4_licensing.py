from __future__ import annotations

from fastapi.testclient import TestClient

from doobielogic.api_v4 import app
from doobielogic.license_store import LicenseStore
from doobielogic.runtime_config import load_shared_storage_config


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


def test_license_validation_accepts_authorization_bearer_service_key(monkeypatch, tmp_path):
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
            "notes": "",
        },
    )
    customer_id = customer.json()["customer_id"]

    generated = client.post(
        "/api/v1/admin/licenses/generate",
        headers=admin_headers,
        json={"customer_id": customer_id, "plan_type": "standard"},
    )
    license_key = generated.json()["license_key"]

    validated = client.post(
        "/api/v1/license/validate",
        headers={"Authorization": "Bearer service-key"},
        json={"license_key": license_key},
    )
    assert validated.status_code == 200
    assert validated.json()["valid"] is True


def test_license_validation_auth_failure_is_clear(monkeypatch, tmp_path):
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "service-key")
    monkeypatch.setattr("doobielogic.api_v4.LICENSE_STORE", LicenseStore(path=tmp_path / "store.json"))

    missing = client.post("/api/v1/license/validate", json={"license_key": "DB-TRIAL-XXXX-YYYY-ZZZZ"})
    assert missing.status_code == 401
    assert "Missing service API key" in missing.json()["detail"]

    wrong = client.post(
        "/api/v1/license/validate",
        headers={"Authorization": "Bearer wrong-key"},
        json={"license_key": "DB-TRIAL-XXXX-YYYY-ZZZZ"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "Invalid service API key."

    malformed = client.post(
        "/api/v1/license/validate",
        headers={"Authorization": "Token wrong-key"},
        json={"license_key": "DB-TRIAL-XXXX-YYYY-ZZZZ"},
    )
    assert malformed.status_code == 401
    assert "Invalid Authorization header format" in malformed.json()["detail"]
