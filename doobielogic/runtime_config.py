from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    safe = str(value).strip()
    return safe or None


def _first_present(mapping: Mapping[str, Any] | None, keys: tuple[str, ...]) -> str | None:
    if not mapping:
        return None
    for key in keys:
        value = _clean(mapping.get(key))
        if value:
            return value
    return None


def _resolve_setting(
    *,
    env_keys: tuple[str, ...],
    env: Mapping[str, str] | None = None,
    secrets: Mapping[str, Any] | None = None,
    default: str | None = None,
) -> str | None:
    value = _first_present(env or os.environ, env_keys)
    if value:
        return value
    value = _first_present(secrets, env_keys)
    if value:
        return value
    return default


def normalize_base_url(raw: str | None) -> str | None:
    safe = _clean(raw)
    if not safe:
        return None
    return safe.rstrip("/")


@dataclass(frozen=True)
class SharedStorageConfig:
    license_store_path: str
    key_db_path: str


@dataclass(frozen=True)
class FastAPIRuntimeConfig:
    service_api_key: str
    admin_api_key: str
    key_validation_token: str
    storage: SharedStorageConfig


@dataclass(frozen=True)
class BuyerDashboardConfig:
    base_url: str | None
    api_key: str | None


def load_shared_storage_config(
    *,
    env: Mapping[str, str] | None = None,
    secrets: Mapping[str, Any] | None = None,
) -> SharedStorageConfig:
    return SharedStorageConfig(
        license_store_path=_resolve_setting(
            env_keys=("DOOBIE_LICENSE_STORE",),
            env=env,
            secrets=secrets,
            default="data/license_store.json",
        )
        or "data/license_store.json",
        key_db_path=_resolve_setting(
            env_keys=("DOOBIE_KEY_DB",),
            env=env,
            secrets=secrets,
            default="data/key_store.db",
        )
        or "data/key_store.db",
    )


def load_fastapi_runtime_config(env: Mapping[str, str] | None = None) -> FastAPIRuntimeConfig:
    safe_env = env or os.environ
    return FastAPIRuntimeConfig(
        service_api_key=_resolve_setting(env_keys=("DOOBIE_API_KEY",), env=safe_env, default="") or "",
        admin_api_key=_resolve_setting(env_keys=("ADMIN_API_KEY",), env=safe_env, default="") or "",
        key_validation_token=_resolve_setting(env_keys=("DOOBIE_KEY_VALIDATION_TOKEN",), env=safe_env, default="") or "",
        storage=load_shared_storage_config(env=safe_env),
    )


def load_buyer_dashboard_config(
    *,
    env: Mapping[str, str] | None = None,
    secrets: Mapping[str, Any] | None = None,
) -> BuyerDashboardConfig:
    base_url = normalize_base_url(
        _resolve_setting(
            env_keys=("DOOBIE_BASE_URL", "DOOBIELOGIC_URL"),
            env=env,
            secrets=secrets,
            default=None,
        )
    )
    api_key = _resolve_setting(
        env_keys=("DOOBIE_API_KEY", "DOOBIELOGIC_API_KEY"),
        env=env,
        secrets=secrets,
        default=None,
    )
    return BuyerDashboardConfig(base_url=base_url, api_key=api_key)
