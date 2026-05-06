from doobielogic.config import load_doobie_config
from doobielogic.key_management import KeyStore
from doobielogic.license_store import LicenseStore


def test_database_url_configured_sets_postgres_backends_without_connection(monkeypatch, tmp_path):
    monkeypatch.setattr("doobielogic.key_management.init_postgres_schema", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("doobielogic.license_store.init_postgres_schema", lambda *_args, **_kwargs: None)

    store = KeyStore(path=tmp_path / "keys.db", database_url="postgresql://user:pass@db:5432/app")
    lic = LicenseStore(path=tmp_path / "licenses.json", database_url="postgresql://user:pass@db:5432/app")

    assert store.diagnostic()["backend"] == "postgres"
    assert lic.diagnostic()["backend"] == "postgres"


def test_no_database_url_falls_back_to_local_backends(tmp_path):
    store = KeyStore(path=tmp_path / "keys.db", database_url="")
    lic = LicenseStore(path=tmp_path / "licenses.json", database_url="")

    assert store.diagnostic()["backend"] == "local_sqlite"
    assert lic.diagnostic()["backend"] == "local_sqlite"


def test_production_like_local_mode_warns_for_deployment_local_data():
    cfg = load_doobie_config(
        env={
            "DOOBIE_ENV": "production",
            "DOOBIE_BACKEND_MODE": "local",
        }
    )
    warnings = cfg.diagnostics()["warnings"]
    assert "PRODUCTION_CONFIG_DRIFT_RISK_LOCAL_MODE_ACTIVE" in warnings
    assert "Keys and licenses are deployment-local and may not survive redeploys." in warnings


def test_backend_mode_accepts_postgres_alias():
    cfg = load_doobie_config(
        env={
            "DOOBIE_BACKEND_MODE": "postgres",
            "DOOBIE_ADMIN_API_BASE_URL": "https://admin.example.com",
        }
    )
    assert cfg.backend_mode == "remote_api"
