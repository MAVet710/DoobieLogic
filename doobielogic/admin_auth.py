from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import bcrypt


@dataclass(frozen=True)
class AdminAuthConfig:
    username: str | None
    password_hash: str | None


SECRET_USERNAME_KEYS: tuple[str, ...] = ("DOOBIE_ADMIN_USERNAME", "ADMIN_USERNAME")
SECRET_PASSWORD_HASH_KEYS: tuple[str, ...] = ("DOOBIE_ADMIN_PASSWORD_HASH", "ADMIN_PASSWORD_HASH")


def _first_present(settings: Mapping[str, str] | None, keys: tuple[str, ...]) -> str | None:
    if not settings:
        return None
    for key in keys:
        value = settings.get(key)
        if value is None:
            continue
        safe_value = value.strip()
        if safe_value:
            return safe_value
    return None


def load_admin_auth_config(
    secrets: Mapping[str, str] | None,
    env: Mapping[str, str] | None = None,
) -> AdminAuthConfig:
    username = _first_present(secrets, SECRET_USERNAME_KEYS)
    password_hash = _first_present(secrets, SECRET_PASSWORD_HASH_KEYS)

    if env:
        username = username or _first_present(env, SECRET_USERNAME_KEYS)
        password_hash = password_hash or _first_present(env, SECRET_PASSWORD_HASH_KEYS)

    return AdminAuthConfig(username=username, password_hash=password_hash)


SECRET_USERNAME_KEYS: tuple[str, ...] = ("DOOBIE_ADMIN_USERNAME", "ADMIN_USERNAME")
SECRET_PASSWORD_HASH_KEYS: tuple[str, ...] = ("DOOBIE_ADMIN_PASSWORD_HASH", "ADMIN_PASSWORD_HASH")
SESSION_AUTH_KEY = "admin_authenticated"


@dataclass(frozen=True)
class AdminAuthConfig:
    username: str | None
    password_hash: str | None


def _first_present(source: Mapping[str, object] | None, keys: tuple[str, ...]) -> str | None:
    if not source:
        return None
    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        safe_value = str(value).strip()
        if safe_value:
            return safe_value
    return None


def _compat_from_auth_admins(source: Mapping[str, object] | None) -> tuple[str | None, str | None]:
    """Compatibility fallback for Streamlit secrets shaped as [auth.admins]."""
    if not source:
        return None, None

    auth_block = source.get("auth")
    if not isinstance(auth_block, Mapping):
        return None, None

    admins_block = auth_block.get("admins")
    if not isinstance(admins_block, Mapping) or not admins_block:
        return None, None

    first_user = next(iter(admins_block.items()))
    username = str(first_user[0]).strip()
    password_hash = str(first_user[1]).strip()
    if not username or not password_hash:
        return None, None
    return username, password_hash


def load_admin_auth_config(
    secrets: Mapping[str, object] | None,
    env: Mapping[str, str] | None = None,
) -> AdminAuthConfig:
    username = _first_present(secrets, SECRET_USERNAME_KEYS)
    password_hash = _first_present(secrets, SECRET_PASSWORD_HASH_KEYS)

    compat_user, compat_hash = _compat_from_auth_admins(secrets)
    username = username or compat_user
    password_hash = password_hash or compat_hash

    if env:
        username = username or _first_present(env, SECRET_USERNAME_KEYS)
        password_hash = password_hash or _first_present(env, SECRET_PASSWORD_HASH_KEYS)

    return AdminAuthConfig(username=username, password_hash=password_hash)


def verify_admin_credentials(username: str, password: str, config: AdminAuthConfig) -> bool:
    if not config.password_hash:
        return False

    safe_user = (username or "").strip()
    safe_password = password or ""
    if not safe_password:
        return False

    if config.username and safe_user != config.username:
        return False

    try:
        return bcrypt.checkpw(safe_password.encode("utf-8"), config.password_hash.encode("utf-8"))
    except ValueError:
        return False


def ensure_admin_session_state() -> None:
    if SESSION_AUTH_KEY not in st.session_state:
        st.session_state[SESSION_AUTH_KEY] = False


def require_admin_auth(*, form_key: str, submit_label: str) -> bool:
    ensure_admin_session_state()

    config = load_admin_auth_config(st.secrets if hasattr(st, "secrets") else None, os.environ)
    if not config.password_hash:
        st.error("Admin credentials not configured")
        return False

    return verify_admin_credentials(safe_user, safe_password, AdminAuthConfig(username=safe_user, password_hash=stored))


def verify_admin_credentials(username: str, password: str, config: AdminAuthConfig) -> bool:
    safe_password = password or ""
    if not safe_password or not config.password_hash:
        return False

    if config.username:
        safe_user = (username or "").strip()
        if not safe_user:
            return False
        if safe_user != config.username:
            return False

    try:
        return bcrypt.checkpw(safe_password.encode("utf-8"), config.password_hash.encode("utf-8"))
    except ValueError:
        return False
