from doobielogic.admin_auth import AdminAuthConfig, load_admin_auth_config, verify_admin_credentials, verify_admin_password


TEST_USERNAME = "test-admin"
TEST_PASSWORD = "doobielogic-test-admin-2026"
TEST_PASSWORD_HASH = "$2b$12$MoP2N.Y9hPY747f4sUnRNejdz.9wtfCFCbKc8W5Oe1xmrcHDx6KTi"


def test_verify_admin_credentials_bcrypt_success_and_failures():
    config = AdminAuthConfig(
        username=TEST_USERNAME,
        password_hash=TEST_PASSWORD_HASH,
    )
    assert verify_admin_credentials(TEST_USERNAME, TEST_PASSWORD, config) is True
    assert verify_admin_credentials("wrong", TEST_PASSWORD, config) is False
    assert verify_admin_credentials(TEST_USERNAME, "wrong", config) is False


def test_verify_admin_credentials_requires_username_when_configured():
    config = AdminAuthConfig(
        username=TEST_USERNAME,
        password_hash=TEST_PASSWORD_HASH,
    )
    assert verify_admin_credentials(TEST_USERNAME, TEST_PASSWORD, config) is True
    assert verify_admin_credentials("not-test-admin", TEST_PASSWORD, config) is False
    assert verify_admin_credentials(TEST_USERNAME, "wrong", config) is False


def test_verify_admin_credentials_supports_password_only_mode():
    config = AdminAuthConfig(
        username=None,
        password_hash=TEST_PASSWORD_HASH,
    )
    assert verify_admin_credentials("", TEST_PASSWORD, config) is True


def test_load_admin_auth_config_prefers_doobie_keys_and_supports_fallback_keys():
    primary = {
        "DOOBIE_ADMIN_USERNAME": TEST_USERNAME,
        "DOOBIE_ADMIN_PASSWORD_HASH": TEST_PASSWORD_HASH,
        "ADMIN_USERNAME": "alt",
        "ADMIN_PASSWORD_HASH": "alt_hash",
    }
    primary_cfg = load_admin_auth_config(primary, None)
    assert primary_cfg.username == TEST_USERNAME
    assert primary_cfg.password_hash == TEST_PASSWORD_HASH

    fallback = {
        "ADMIN_USERNAME": TEST_USERNAME,
        "ADMIN_PASSWORD_HASH": TEST_PASSWORD_HASH,
    }
    fallback_cfg = load_admin_auth_config(fallback, None)
    assert fallback_cfg.username == TEST_USERNAME
    assert fallback_cfg.password_hash == TEST_PASSWORD_HASH


def test_load_admin_auth_config_has_no_public_default_credentials():
    cfg = load_admin_auth_config({}, {})
    assert cfg.username is None
    assert cfg.password_hash is None
    assert verify_admin_credentials(TEST_USERNAME, TEST_PASSWORD, cfg) is False
