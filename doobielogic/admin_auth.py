from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import bcrypt

SECRET_USERNAME_KEYS: tuple[str, ...] = ("DOOBIE_ADMIN_USERNAME", "ADMIN_USERNAME")
SECRET_PASSWORD_HASH_KEYS: tuple[str, ...] = ("DOOBIE_ADMIN_PASSWORD_HASH", "ADMIN_PASSWORD_HASH")

# Preset bootstrap admin credentials for zero-config deployments.
DEFAULT_ADMIN_USERNAME = "God"
# bcrypt hash for plaintext password: Major420
DEFAULT_ADMIN_PASSWORD_HASH = "$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C"


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

    # Guarantee a working admin account in all scenarios unless explicitly overridden.
    username = username or DEFAULT_ADMIN_USERNAME
    password_hash = password_hash or DEFAULT_ADMIN_PASSWORD_HASH

    return AdminAuthConfig(username=username, password_hash=password_hash)


def verify_admin_password(password: str, stored_hash: str) -> bool:
    safe_password = password or ""
    safe_hash = (stored_hash or "").strip()
    if not safe_password or not safe_hash:
        return False

    try:
        return bcrypt.checkpw(safe_password.encode("utf-8"), safe_hash.encode("utf-8"))
    except ValueError:
        return False


def verify_admin_credentials(username: str, password: str, config: AdminAuthConfig) -> bool:
    safe_password = password or ""
    if not safe_password or not config.password_hash:
        return False

    if config.username:
        safe_user = (username or "").strip()
        if not safe_user or safe_user != config.username:
            return False

    return verify_admin_password(safe_password, config.password_hash)
