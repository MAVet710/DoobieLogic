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


def verify_admin_password(username: str, password: str, admins: Mapping[str, str] | None) -> bool:
    if not admins:
        return False

    safe_user = (username or "").strip()
    safe_password = password or ""
    if not safe_user or not safe_password:
        return False

    stored = admins.get(safe_user)
    if not stored:
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
