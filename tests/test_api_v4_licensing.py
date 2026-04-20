from __future__ import annotations

from fastapi.testclient import TestClient

from doobielogic.api_v4 import app
from doobielogic.key_management import KeyStore
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
    assert "Invalid service API key" in wrong.json()["detail"]
    assert "storage mismatch" in wrong.json()["detail"]

    malformed = client.post(
        "/api/v1/license/validate",
        headers={"Authorization": "Token wrong-key"},
        json={"license_key": "DB-TRIAL-XXXX-YYYY-ZZZZ"},
    )
    assert malformed.status_code == 401
    assert "Invalid Authorization header format" in malformed.json()["detail"]


def test_admin_api_key_management_routes(monkeypatch, tmp_path):
    monkeypatch.setattr("doobielogic.api_v4.ADMIN_API_KEY", "admin-secret")
    monkeypatch.setattr("doobielogic.api_v4.KEY_STORE", KeyStore(path=tmp_path / "keys.db"))
    headers = {"Authorization": "Bearer admin-secret"}

    created = client.post(
        "/api/v1/admin/api-keys/generate",
        headers=headers,
        json={
            "company_name": "Acme",
            "label": "Buyer Dashboard",
            "scope": "buyer_dashboard",
            "expires_at": "2030-01-01",
            "notes": "integration",
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["raw_key"].startswith("DLB-API-")

    listed = client.get("/api/v1/admin/api-keys", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["keys"]) == 1

    rec_id = payload["record_id"]
    updated = client.post(
        "/api/v1/admin/api-keys/update",
        headers=headers,
        json={"record_id": rec_id, "tier_or_scope": "buyer_dashboard,admin"},
    )
    assert updated.status_code == 200

    revoked = client.post("/api/v1/admin/api-keys/revoke", headers=headers, json={"record_id": rec_id})
    assert revoked.status_code == 200



def test_bootstrap_admin_key_and_use_for_admin_routes(monkeypatch, tmp_path):
    monkeypatch.setattr("doobielogic.api_v4.ADMIN_API_KEY", "")
    monkeypatch.setattr("doobielogic.api_v4.KEY_STORE", KeyStore(path=tmp_path / "keys.db"))
    monkeypatch.setattr("doobielogic.api_v4.LICENSE_STORE", LicenseStore(path=tmp_path / "store.json"))

    status = client.get("/api/v1/admin/bootstrap/status")
    assert status.status_code == 200
    assert status.json()["bootstrap_mode"] is True

    generated = client.post(
        "/api/v1/admin/bootstrap/generate",
        json={"label": "Initial Bootstrap Admin Key", "notes": "first-run"},
    )
    assert generated.status_code == 200
    admin_key = generated.json()["raw_key"]

    list_customers = client.get("/api/v1/admin/customers", headers={"Authorization": f"Bearer {admin_key}"})
    assert list_customers.status_code == 200
    assert list_customers.json() == {"customers": []}


def test_bootstrap_closed_after_admin_key_exists(monkeypatch, tmp_path):
    monkeypatch.setattr("doobielogic.api_v4.ADMIN_API_KEY", "")
    monkeypatch.setattr("doobielogic.api_v4.KEY_STORE", KeyStore(path=tmp_path / "keys.db"))

    first = client.post("/api/v1/admin/bootstrap/generate", json={"label": "Initial Bootstrap Admin Key", "notes": ""})
    assert first.status_code == 200

    second = client.post("/api/v1/admin/bootstrap/generate", json={"label": "Second", "notes": ""})
    assert second.status_code == 409


def test_bootstrap_key_can_manage_additional_admin_and_service_keys(monkeypatch, tmp_path):
    monkeypatch.setattr("doobielogic.api_v4.ADMIN_API_KEY", "")
    monkeypatch.setattr("doobielogic.api_v4.KEY_STORE", KeyStore(path=tmp_path / "keys.db"))

    bootstrap = client.post("/api/v1/admin/bootstrap/generate", json={"label": "Initial Bootstrap Admin Key", "notes": ""})
    assert bootstrap.status_code == 200
    admin_headers = {"Authorization": f"Bearer {bootstrap.json()['raw_key']}"}

    create_admin = client.post(
        "/api/v1/admin/api-keys/admin/generate",
        headers=admin_headers,
        json={"label": "Ops Admin", "notes": "secondary"},
    )
    assert create_admin.status_code == 200
    assert create_admin.json()["raw_key"].startswith("DLB-ADM-")

    create_service = client.post(
        "/api/v1/admin/api-keys/generate",
        headers=admin_headers,
        json={
            "company_name": "Buyer Dashboard",
            "label": "Buyer API",
            "scope": "buyer_dashboard",
            "notes": "integration",
        },
    )
    assert create_service.status_code == 200
    service_key = create_service.json()["raw_key"]
    assert service_key.startswith("DLB-API-")

    validate_service = client.post("/api/v1/keys/validate", json={"api_key": service_key})
    assert validate_service.status_code == 200
    assert validate_service.json()["valid"] is True


def test_service_endpoints_reject_admin_keys(monkeypatch, tmp_path):
    monkeypatch.setattr("doobielogic.api_v4.ADMIN_API_KEY", "")
    monkeypatch.setattr("doobielogic.api_v4.API_KEY", "")
    key_store = KeyStore(path=tmp_path / "keys.db")
    monkeypatch.setattr("doobielogic.api_v4.KEY_STORE", key_store)

    admin = key_store.create_admin_api_key(label="Admin")
    res = client.post(
        "/api/v1/license/validate",
        headers={"Authorization": f"Bearer {admin.raw_key}"},
        json={"license_key": "DB-TRIAL-XXXX-YYYY-ZZZZ"},
    )
    assert res.status_code == 401
    assert "Invalid service API key" in res.json()["detail"]
