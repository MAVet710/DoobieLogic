from __future__ import annotations

from datetime import datetime, timedelta, timezone

from doobielogic.license_store import LicenseStore


def test_customer_creation_and_license_generation(tmp_path):
    store = LicenseStore(path=tmp_path / "license_store.json")
    customer = store.create_customer("Acme Cannabis", "Pat", "pat@example.com", "priority account")
    assert customer.customer_id

    license_obj = store.create_license(customer.customer_id, "premium")
    assert license_obj.license_key.startswith("DLB-LIC-")
    assert license_obj.status == "active"


def test_license_validation_success_updates_last_validated(tmp_path):
    store = LicenseStore(path=tmp_path / "license_store.json")
    customer = store.create_customer("Acme Cannabis", "Pat", "pat@example.com")
    license_obj = store.create_license(customer.customer_id, "standard")

    result = store.validate_license(license_obj.license_key)
    assert result["valid"] is True
    assert result["plan_type"] == "standard"
    refreshed = store.find_license_by_key(license_obj.license_key)
    assert refreshed is not None
    assert refreshed.last_validated_at is not None


def test_revoked_or_expired_license_fails_validation(tmp_path):
    store = LicenseStore(path=tmp_path / "license_store.json")
    customer = store.create_customer("Acme Cannabis", "Pat", "pat@example.com")

    revoked = store.create_license(customer.customer_id, "trial")
    store.revoke_license(revoked.license_key, "billing")
    revoked_result = store.validate_license(revoked.license_key)
    assert revoked_result == {"valid": False, "reason": "revoked"}

    expired_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    expired = store.create_license(customer.customer_id, "trial", expires_at=expired_at)
    expired_result = store.validate_license(expired.license_key)
    assert expired_result == {"valid": False, "reason": "expired"}


def test_reset_generates_new_key_and_invalidates_old(tmp_path):
    store = LicenseStore(path=tmp_path / "license_store.json")
    customer = store.create_customer("Acme Cannabis", "Pat", "pat@example.com")
    license_obj = store.create_license(customer.customer_id, "enterprise")

    reset = store.reset_license(license_obj.license_key, reason="customer requested reset")
    assert reset["old"].status == "revoked"
    assert reset["new"].license_key != reset["old"].license_key
    assert reset["new"].reset_count == reset["old"].reset_count + 1

    old_result = store.validate_license(reset["old"].license_key)
    new_result = store.validate_license(reset["new"].license_key)
    assert old_result == {"valid": False, "reason": "revoked"}
    assert new_result["valid"] is True
