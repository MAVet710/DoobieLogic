from datetime import date, timedelta

from doobielogic.key_management import KEY_ROLE_ADMIN, KeyStore


def test_api_key_generation_and_validation(tmp_path):
    store = KeyStore(path=tmp_path / "keys.db")
    generated = store.create_api_key(
        company_name="Acme Cannabis",
        label="Buyer Dashboard",
        scope="buyer_dashboard,read_only",
        expiration_date=None,
        notes="integration key",
    )

    records = store.load_key_records(key_type="api", key_role="service")
    assert len(records) == 1
    assert records[0]["key_preview"] == generated.raw_key[-8:]
    assert generated.raw_key not in str(records[0])

    result = store.validate_api_key(generated.raw_key)
    assert result["valid"] is True
    assert result["company"] == "Acme Cannabis"
    assert "buyer_dashboard" in result["permissions"]
    assert "expires_at" in result


def test_api_key_revoked_expired_and_disabled(tmp_path):
    store = KeyStore(path=tmp_path / "keys.db")
    expired = store.create_api_key(
        company_name="Acme Cannabis",
        label="Expired",
        scope="buyer_dashboard",
        expiration_date=date.today() - timedelta(days=1),
        notes="",
    )
    expired_result = store.validate_api_key(expired.raw_key)
    assert expired_result["valid"] is False
    assert expired_result["reason"] == "expired"

    active = store.create_api_key(
        company_name="Acme Cannabis",
        label="Active",
        scope="buyer_dashboard",
        expiration_date=None,
        notes="",
    )
    record = store.load_key_records(key_type="api", key_role="service")[0]
    store.toggle_key_status(record["id"], is_active=False)
    disabled_result = store.validate_api_key(active.raw_key)
    assert disabled_result["valid"] is False
    assert disabled_result["reason"] == "disabled"

    store.toggle_key_status(record["id"], is_active=True)
    store.revoke_key(record["id"])
    revoked_result = store.validate_api_key(active.raw_key)
    assert revoked_result["valid"] is False
    assert revoked_result["reason"] == "revoked"


def test_admin_key_bootstrap_and_role_separation(tmp_path):
    store = KeyStore(path=tmp_path / "keys.db")
    assert store.has_active_admin_key() is False

    admin = store.create_admin_api_key(label="Initial Bootstrap Admin Key", is_bootstrap=True)
    assert store.has_active_admin_key() is True

    admin_records = store.load_key_records(key_type="api", key_role=KEY_ROLE_ADMIN)
    assert len(admin_records) == 1
    assert int(admin_records[0]["is_bootstrap"]) == 1

    as_service = store.validate_api_key(admin.raw_key)
    assert as_service["valid"] is False
    assert as_service["reason"] == "wrong_key_type"

    as_admin = store.validate_admin_key(admin.raw_key)
    assert as_admin["valid"] is True
    assert as_admin["key_role"] == "admin"
