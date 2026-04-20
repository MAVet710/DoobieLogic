from __future__ import annotations

import os
from dataclasses import dataclass


def _parse_bool(value: str | None) -> bool:
    safe = (value or "").strip().lower()
    return safe in {"1", "true", "yes", "on"}


def _is_production_like_env(source: dict[str, str]) -> bool:
    doobie_env = (source.get("DOOBIE_ENV") or "").strip().lower()
    if doobie_env in {"prod", "production", "staging"}:
        return True
    return any(
        bool((source.get(name) or "").strip())
        for name in ("RENDER", "RENDER_SERVICE_NAME", "RENDER_EXTERNAL_URL", "RENDER_GIT_COMMIT")
    )


def _resolve_backend_mode(preferred_mode: str, base_url: str) -> tuple[str, str]:
    normalized_mode = preferred_mode.strip().lower()
    if normalized_mode in {"", "auto"}:
        return ("remote_api", "auto") if base_url else ("local", "auto")
    if normalized_mode in {"remote", "remote_api"}:
        return "remote_api", "explicit"
    if normalized_mode == "local":
        return "local", "explicit"
    raise ValueError(f"Unsupported DOOBIE_BACKEND_MODE: {preferred_mode!r}. Use one of: auto, local, remote_api.")


@dataclass(frozen=True)
class DoobieConfig:
    api_key: str
    admin_api_key: str
    admin_api_base_url: str
    admin_api_timeout: float
    license_store_path: str
    key_store_path: str
    key_validation_token: str
    backend_mode_value: str
    backend_mode_source: str
    preferred_backend_mode: str
    strict_config: bool
    production_like_env: bool

    @property
    def backend_mode(self) -> str:
        return self.backend_mode_value

    @property
    def remote_ready(self) -> bool:
        return self.backend_mode == "remote_api" and bool(self.admin_api_key)

    def diagnostics(self) -> dict[str, object]:
        warnings: list[str] = []
        if self.backend_mode == "remote_api" and not self.admin_api_key:
            warnings.append("REMOTE_API_MODE_MISSING_ADMIN_API_KEY")
        if self.backend_mode == "local" and self.admin_api_key:
            warnings.append("ADMIN_API_KEY_SET_BUT_REMOTE_MODE_DISABLED")
            if self.production_like_env:
                warnings.append("PRODUCTION_CONFIG_DRIFT_RISK_LOCAL_MODE_ACTIVE")
        if self.backend_mode_source == "auto":
            warnings.append("BACKEND_MODE_AUTO_DETECTED")
        if not self.api_key:
            warnings.append("SERVICE_API_KEY_NOT_SET")
        return {
            "backend_mode": self.backend_mode,
            "backend_mode_source": self.backend_mode_source,
            "preferred_backend_mode": self.preferred_backend_mode,
            "admin_api_base_url": self.admin_api_base_url or None,
            "admin_api_timeout_seconds": self.admin_api_timeout,
            "license_store_path": self.license_store_path,
            "key_store_path": self.key_store_path,
            "admin_api_key_configured": bool(self.admin_api_key),
            "service_api_key_configured": bool(self.api_key),
            "key_validation_token_configured": bool(self.key_validation_token),
            "strict_config": self.strict_config,
            "production_like_env": self.production_like_env,
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
    preferred_mode = (source.get("DOOBIE_BACKEND_MODE") or "auto").strip().lower()
    strict_config = _parse_bool(source.get("DOOBIE_STRICT_CONFIG"))
    production_like_env = _is_production_like_env(source)
    resolved_mode, mode_source = _resolve_backend_mode(preferred_mode, base_url)

    if resolved_mode == "remote_api" and not base_url:
        raise ValueError("DOOBIE_BACKEND_MODE=remote_api requires DOOBIE_ADMIN_API_BASE_URL to be set.")

    if strict_config and resolved_mode == "local" and (source.get("ADMIN_API_KEY") or "").strip() and not base_url:
        raise ValueError(
            "Strict config error: ADMIN_API_KEY is set while backend mode resolved to local and "
            "DOOBIE_ADMIN_API_BASE_URL is missing."
        )

    if production_like_env and strict_config and resolved_mode == "local" and (source.get("ADMIN_API_KEY") or "").strip() and not base_url:
        raise ValueError(
            "Production-like strict config error: local backend mode would drift from remote admin storage. "
            "Set DOOBIE_BACKEND_MODE=remote_api and DOOBIE_ADMIN_API_BASE_URL."
        )

    return DoobieConfig(
        api_key=(source.get("DOOBIE_API_KEY") or "").strip(),
        admin_api_key=(source.get("ADMIN_API_KEY") or "").strip(),
        admin_api_base_url=base_url,
        admin_api_timeout=timeout_value if timeout_value > 0 else 12.0,
        license_store_path=(source.get("DOOBIE_LICENSE_STORE") or "data/license_store.json").strip(),
        key_store_path=(source.get("DOOBIE_KEY_DB") or "data/key_store.db").strip(),
        key_validation_token=(source.get("DOOBIE_KEY_VALIDATION_TOKEN") or "").strip(),
        backend_mode_value=resolved_mode,
        backend_mode_source=mode_source,
        preferred_backend_mode=preferred_mode or "auto",
        strict_config=strict_config,
        production_like_env=production_like_env,
    )
