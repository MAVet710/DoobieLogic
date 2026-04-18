from doobielogic.admin_auth import (
    AdminAuthConfig,
    load_admin_auth_config,
    verify_admin_credentials,
)


def test_verify_admin_credentials_bcrypt_success_and_failures():
    config = AdminAuthConfig(
        username="God",
        password_hash="$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C",
    )
    assert verify_admin_credentials("God", "Major420", config) is True
    assert verify_admin_credentials("wrong", "Major420", config) is False
    assert verify_admin_credentials("God", "wrong", config) is False


def test_load_admin_auth_config_supports_required_secret_names_and_fallbacks():
    primary_cfg = load_admin_auth_config(
        {
            "DOOBIE_ADMIN_USERNAME": "God",
            "DOOBIE_ADMIN_PASSWORD_HASH": "$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C",
            "ADMIN_USERNAME": "backup",
            "ADMIN_PASSWORD_HASH": "backup_hash",
        },
        None,
    )
    assert primary_cfg.username == "God"
    assert primary_cfg.password_hash == "$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C"

    fallback_cfg = load_admin_auth_config(
        {
            "ADMIN_USERNAME": "God",
            "ADMIN_PASSWORD_HASH": "$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C",
        },
        None,
    )
    assert fallback_cfg.username == "God"
    assert fallback_cfg.password_hash == "$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C"


def test_load_admin_auth_config_supports_auth_admins_compat_shape():
    cfg = load_admin_auth_config(
        {
            "auth": {
                "admins": {
                    "God": "$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C",
                }
            }
        },
        None,
    )
    assert cfg.username == "God"
    assert cfg.password_hash == "$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C"
