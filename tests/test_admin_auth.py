from doobielogic.admin_auth import AdminAuthConfig, load_admin_auth_config, verify_admin_credentials, verify_admin_password


def test_verify_admin_credentials_bcrypt_success_and_failures():
    config = AdminAuthConfig(
        username="God",
        password_hash="$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C",
    )
    assert verify_admin_credentials("God", "Major420", config) is True
    assert verify_admin_credentials("wrong", "Major420", config) is False
    assert verify_admin_credentials("God", "wrong", config) is False


def test_verify_admin_credentials_requires_username_when_configured():
    config = AdminAuthConfig(
        username="God",
        password_hash="$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C",
    )
    assert verify_admin_credentials("God", "Major420", config) is True
    assert verify_admin_credentials("not-god", "Major420", config) is False
    assert verify_admin_credentials("God", "wrong", config) is False


def test_verify_admin_credentials_supports_password_only_mode():
    config = AdminAuthConfig(
        username=None,
        password_hash="$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C",
    )
    assert verify_admin_credentials("", "Major420", config) is True


def test_load_admin_auth_config_prefers_doobie_keys_and_supports_fallback_keys():
    primary = {
        "DOOBIE_ADMIN_USERNAME": "God",
        "DOOBIE_ADMIN_PASSWORD_HASH": "$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C",
        "ADMIN_USERNAME": "alt",
        "ADMIN_PASSWORD_HASH": "alt_hash",
    }
    primary_cfg = load_admin_auth_config(primary, None)
    assert primary_cfg.username == "God"
    assert primary_cfg.password_hash == "$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C"

    fallback = {
        "ADMIN_USERNAME": "God",
        "ADMIN_PASSWORD_HASH": "$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C",
    }
    fallback_cfg = load_admin_auth_config(fallback, None)
    assert fallback_cfg.username == "God"
    assert fallback_cfg.password_hash == "$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C"
