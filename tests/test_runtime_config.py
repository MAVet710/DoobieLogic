from __future__ import annotations

from doobielogic.runtime_config import (
    load_buyer_dashboard_config,
    load_fastapi_runtime_config,
    load_shared_storage_config,
)


def test_shared_storage_config_prefers_env_values():
    config = load_shared_storage_config(
        env={
            "DOOBIE_LICENSE_STORE": "/shared/license_store.json",
            "DOOBIE_KEY_DB": "/shared/key_store.db",
        }
    )
    assert config.license_store_path == "/shared/license_store.json"
    assert config.key_db_path == "/shared/key_store.db"


def test_shared_storage_config_supports_streamlit_secrets_fallback():
    config = load_shared_storage_config(
        env={},
        secrets={
            "DOOBIE_LICENSE_STORE": "/secrets/license_store.json",
            "DOOBIE_KEY_DB": "/secrets/key_store.db",
        },
    )
    assert config.license_store_path == "/secrets/license_store.json"
    assert config.key_db_path == "/secrets/key_store.db"


def test_fastapi_runtime_config_loads_api_and_storage_settings():
    config = load_fastapi_runtime_config(
        {
            "DOOBIE_API_KEY": "service-key",
            "ADMIN_API_KEY": "admin-key",
            "DOOBIE_KEY_VALIDATION_TOKEN": "validator-key",
            "DOOBIE_LICENSE_STORE": "/shared/license_store.json",
            "DOOBIE_KEY_DB": "/shared/key_store.db",
        }
    )
    assert config.service_api_key == "service-key"
    assert config.admin_api_key == "admin-key"
    assert config.key_validation_token == "validator-key"
    assert config.storage.license_store_path == "/shared/license_store.json"
    assert config.storage.key_db_path == "/shared/key_store.db"


def test_buyer_dashboard_config_supports_alias_env_vars_and_normalizes_url():
    config = load_buyer_dashboard_config(
        env={
            "DOOBIELOGIC_URL": "https://doobie-api.onrender.com/",
            "DOOBIELOGIC_API_KEY": "service-key",
        }
    )
    assert config.base_url == "https://doobie-api.onrender.com"
    assert config.api_key == "service-key"
