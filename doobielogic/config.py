from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DoobieConfig:
    api_key: str
    admin_api_key: str
    admin_api_base_url: str
    admin_api_timeout: float
    license_store_path: str
    key_store_path: str
    key_validation_token: str

    @property
    def backend_mode(self) -> str:
        return "remote_api" if self.admin_api_base_url else "local"

    @property
    def remote_ready(self) -> bool:
        return self.backend_mode == "remote_api" and bool(self.admin_api_key)

    def diagnostics(self) -> dict[str, object]:
        warnings: list[str] = []
        if self.backend_mode == "remote_api" and not self.admin_api_key:
            warnings.append("REMOTE_API_MODE_MISSING_ADMIN_API_KEY")
        if self.backend_mode == "local" and self.admin_api_key:
            warnings.append("ADMIN_API_KEY_SET_BUT_REMOTE_MODE_DISABLED")
        if not self.api_key:
            warnings.append("SERVICE_API_KEY_NOT_SET")
        return {
            "backend_mode": self.backend_mode,
            "admin_api_base_url": self.admin_api_base_url or None,
            "admin_api_timeout_seconds": self.admin_api_timeout,
            "license_store_path": self.license_store_path,
            "key_store_path": self.key_store_path,
            "admin_api_key_configured": bool(self.admin_api_key),
            "service_api_key_configured": bool(self.api_key),
            "key_validation_token_configured": bool(self.key_validation_token),
            "warnings": warnings,
        }


def load_doobie_config(env: dict[str, str] | None = None) -> DoobieConfig:
    source = env if env is not None else os.environ
    base_url = (source.get("DOOBIE_ADMIN_API_BASE_URL") or "").strip().rstrip("/")
    timeout_raw = (source.get("DOOBIE_ADMIN_API_TIMEOUT") or "12").strip()
    try:
        timeout_value = float(timeout_raw)
    except ValueError:
        timeout_value = 12.0
    return DoobieConfig(
        api_key=(source.get("DOOBIE_API_KEY") or "").strip(),
        admin_api_key=(source.get("ADMIN_API_KEY") or "").strip(),
        admin_api_base_url=base_url,
        admin_api_timeout=timeout_value if timeout_value > 0 else 12.0,
        license_store_path=(source.get("DOOBIE_LICENSE_STORE") or "data/license_store.json").strip(),
        key_store_path=(source.get("DOOBIE_KEY_DB") or "data/key_store.db").strip(),
        key_validation_token=(source.get("DOOBIE_KEY_VALIDATION_TOKEN") or "").strip(),
    )
