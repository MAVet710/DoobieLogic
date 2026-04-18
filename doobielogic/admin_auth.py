from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import bcrypt


@dataclass(frozen=True)
class AdminAuthConfig:
    username: str | None
    password_hash: str | None
    admins: Mapping[str, str]


SECRET_USERNAME_KEYS: tuple[str, ...] = ("DOOBIE_ADMIN_USERNAME", "ADMIN_USERNAME")
SECRET_PASSWORD_HASH_KEYS: tuple[str, ...] = ("DOOBIE_ADMIN_PASSWORD_HASH", "ADMIN_PASSWORD_HASH")


def _first_present(settings: Mapping[str, str] | None, keys: tuple[str, ...]) -> str | None:
    if not settings:
        return None
    for key in keys:
        value = settings.get(key)
        if value is None:
            continue
        safe_value = str(value).strip()
        if safe_value:
            return safe_value
    return None


def _extract_admins_mapping(secrets: Mapping[str, object] | None) -> dict[str, str]:
    if not secrets:
        return {}

    auth_block = secrets.get("auth")
    if not isinstance(auth_block, Mapping):
        return {}

    admins_block = auth_block.get("admins")
    if not isinstance(admins_block, Mapping):
        return {}

    cleaned: dict[str, str] = {}
    for user, pw_hash in admins_block.items():
        safe_user = str(user).strip()
        safe_hash = str(pw_hash).strip()
        if safe_user and safe_hash:
            cleaned[safe_user] = safe_hash
    return cleaned


def load_admin_auth_config(
    secrets: Mapping[str, object] | None,
    env: Mapping[str, str] | None = None,
) -> AdminAuthConfig:
    username = _first_present(secrets, SECRET_USERNAME_KEYS)  # type: ignore[arg-type]
    password_hash = _first_present(secrets, SECRET_PASSWORD_HASH_KEYS)  # type: ignore[arg-type]
    admins = _extract_admins_mapping(secrets)

    if env:
        username = username or _first_present(env, SECRET_USERNAME_KEYS)
        password_hash = password_hash or _first_present(env, SECRET_PASSWORD_HASH_KEYS)

    return AdminAuthConfig(username=username, password_hash=password_hash, admins=admins)


def _check_bcrypt(password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except ValueError:
        return False


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

    return _check_bcrypt(safe_password, stored)


def verify_admin_credentials(username: str, password: str, config: AdminAuthConfig) -> bool:
    safe_user = (username or "").strip()
    safe_password = password or ""
    if not safe_password:
        return False

    if config.admins:
        if not safe_user:
            return False
        stored = config.admins.get(safe_user)
        if not stored:
            return False
        return _check_bcrypt(safe_password, stored)

    if not config.password_hash:
        return False

    if config.username:
        if not safe_user:
            return False
        if safe_user != config.username:
            return False

    return _check_bcrypt(safe_password, config.password_hash)


def is_admin_auth_configured(config: AdminAuthConfig) -> bool:
    return bool(config.password_hash or config.admins)
