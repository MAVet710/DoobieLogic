from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

import bcrypt
import streamlit as st

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

    if st.session_state.get(SESSION_AUTH_KEY):
        return True

    with st.form(form_key):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button(submit_label)

    if submitted:
        if verify_admin_credentials(username=username, password=password, config=config):
            st.session_state[SESSION_AUTH_KEY] = True
            st.success("Authenticated")
            st.rerun()
        else:
            st.error("Invalid credentials")

    return False


def logout_admin(*, button_key: str) -> None:
    if st.button("Log out", key=button_key):
        st.session_state[SESSION_AUTH_KEY] = False
        st.rerun()
