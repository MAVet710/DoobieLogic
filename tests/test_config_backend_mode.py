from doobielogic.config import load_doobie_config


def test_backend_mode_defaults_to_auto_local_when_remote_url_missing():
    config = load_doobie_config(env={})
    assert config.backend_mode == "local"
    diagnostics = config.diagnostics()
    assert diagnostics["backend_mode_source"] == "auto"
    assert "BACKEND_MODE_AUTO_DETECTED" in diagnostics["warnings"]


def test_backend_mode_auto_uses_remote_when_url_present():
    config = load_doobie_config(
        env={
            "DOOBIE_ADMIN_API_BASE_URL": "https://example.com/",
            "ADMIN_API_KEY": "secret",
        }
    )
    assert config.backend_mode == "remote_api"
    assert config.backend_mode_source == "auto"
    diagnostics = config.diagnostics()
    assert "ADMIN_API_KEY_SET_BUT_REMOTE_MODE_DISABLED" not in diagnostics["warnings"]


def test_backend_mode_can_be_explicitly_set_to_remote():
    config = load_doobie_config(
        env={
            "DOOBIE_BACKEND_MODE": "remote_api",
            "DOOBIE_ADMIN_API_BASE_URL": "https://example.com",
        }
    )
    assert config.backend_mode == "remote_api"
    assert config.backend_mode_source == "explicit"


def test_explicit_remote_mode_requires_base_url():
    try:
        load_doobie_config(env={"DOOBIE_BACKEND_MODE": "remote_api"})
    except ValueError as exc:
        assert "DOOBIE_ADMIN_API_BASE_URL" in str(exc)
    else:
        raise AssertionError("Expected explicit remote mode without base url to fail")


def test_strict_mode_rejects_admin_key_without_remote_url():
    try:
        load_doobie_config(
            env={
                "DOOBIE_STRICT_CONFIG": "true",
                "ADMIN_API_KEY": "secret",
            }
        )
    except ValueError as exc:
        assert "Strict config error" in str(exc)
    else:
        raise AssertionError("Expected strict config to fail when ADMIN_API_KEY is set without remote url")
