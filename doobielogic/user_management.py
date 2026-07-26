from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

import bcrypt

from doobielogic.postgres_persistence import is_postgres_url, postgres_connection


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,120}$")
ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
VALID_PERMISSIONS = {
    "chat",
    "upload_data",
    "manage_users",
    "manage_roles",
    "view_admin",
}
DEFAULT_ROLES: dict[str, tuple[str, tuple[str, ...]]] = {
    "admin": (
        "Administrator",
        ("chat", "upload_data", "manage_users", "manage_roles", "view_admin"),
    ),
    "buyer": ("Buyer", ("chat", "upload_data")),
    "operations": ("Operations", ("chat", "upload_data")),
    "compliance": ("Compliance", ("chat", "upload_data")),
    "analyst": ("Analyst", ("chat", "upload_data")),
    "viewer": ("Viewer", ("chat",)),
}


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_username(username: str | None) -> str:
    return str(username or "").strip().casefold()


def hash_password(password: str) -> str:
    safe = str(password or "")
    if len(safe) < 12:
        raise ValueError("Passwords must contain at least 12 characters.")
    return bcrypt.hashpw(safe.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            str(password or "").encode("utf-8"),
            str(password_hash or "").encode("utf-8"),
        )
    except (TypeError, ValueError):
        return False


def _validate_password_hash(password_hash: str) -> str:
    safe = str(password_hash or "").strip()
    if not safe.startswith(("$2a$", "$2b$", "$2y$")):
        raise ValueError("A bcrypt password hash is required.")
    return safe


def _clean_permissions(permissions: list[str] | tuple[str, ...] | set[str]) -> tuple[str, ...]:
    cleaned = tuple(sorted({str(item).strip().casefold() for item in permissions if str(item).strip()}))
    invalid = set(cleaned) - VALID_PERMISSIONS
    if invalid:
        raise ValueError(f"Unsupported permissions: {', '.join(sorted(invalid))}")
    if "chat" not in cleaned:
        raise ValueError("Every role must include chat access.")
    return cleaned


@dataclass(frozen=True)
class RoleRecord:
    name: str
    display_name: str
    permissions: tuple[str, ...]
    system_role: bool
    active: bool

    def allows(self, permission: str) -> bool:
        return str(permission or "").strip().casefold() in self.permissions


@dataclass(frozen=True)
class UserRecord:
    id: str
    username: str
    normalized_username: str
    display_name: str
    email: str
    password_hash: str
    role: str
    active: bool
    must_change_password: bool
    last_login_at: str | None
    created_at: str | None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class UserStore:
    """Durable DoobieLogic accounts backed by shared Postgres or local SQLite."""

    def __init__(
        self,
        *,
        database_url: str | None = None,
        sqlite_path: str | Path = "data/user_store.db",
    ):
        self.database_url = str(database_url or "").strip() or None
        self.sqlite_path = Path(sqlite_path)
        self.backend = "postgres" if is_postgres_url(self.database_url) else "sqlite"
        self._lock = Lock()
        self._initialize()

    def _sqlite_connect(self) -> sqlite3.Connection:
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        if self.backend == "postgres":
            assert self.database_url
            statements = (
                """
                CREATE TABLE IF NOT EXISTS app_roles (
                    name TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    permissions JSONB NOT NULL DEFAULT '["chat"]'::jsonb,
                    system_role BOOLEAN NOT NULL DEFAULT FALSE,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS app_users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    username TEXT NOT NULL,
                    normalized_username TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL REFERENCES app_roles(name),
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    must_change_password BOOLEAN NOT NULL DEFAULT TRUE,
                    last_login_at TIMESTAMPTZ,
                    password_changed_at TIMESTAMPTZ,
                    created_by TEXT,
                    updated_by TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """,
                "CREATE INDEX IF NOT EXISTS idx_app_users_role ON app_users(role)",
                "CREATE INDEX IF NOT EXISTS idx_app_users_active ON app_users(active)",
            )
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    for statement in statements:
                        cur.execute(statement)
        else:
            with self._sqlite_connect() as conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS app_roles (
                        name TEXT PRIMARY KEY,
                        display_name TEXT NOT NULL,
                        permissions TEXT NOT NULL,
                        system_role INTEGER NOT NULL DEFAULT 0,
                        active INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS app_users (
                        id TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        normalized_username TEXT NOT NULL UNIQUE,
                        display_name TEXT NOT NULL DEFAULT '',
                        email TEXT NOT NULL DEFAULT '',
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL REFERENCES app_roles(name),
                        active INTEGER NOT NULL DEFAULT 1,
                        must_change_password INTEGER NOT NULL DEFAULT 1,
                        last_login_at TEXT,
                        password_changed_at TEXT,
                        created_by TEXT,
                        updated_by TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_app_users_role ON app_users(role);
                    CREATE INDEX IF NOT EXISTS idx_app_users_active ON app_users(active);
                    """
                )
                conn.commit()
        self._ensure_default_roles()

    def _ensure_default_roles(self) -> None:
        for name, (display_name, permissions) in DEFAULT_ROLES.items():
            if self.get_role(name):
                continue
            self._insert_role(name, display_name, permissions, system_role=True)

    def _insert_role(
        self,
        name: str,
        display_name: str,
        permissions: tuple[str, ...],
        *,
        system_role: bool,
    ) -> RoleRecord:
        now = utcnow_iso()
        if self.backend == "postgres":
            assert self.database_url
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO app_roles(name, display_name, permissions, system_role, active)
                        VALUES (%s, %s, %s::jsonb, %s, TRUE)
                        """,
                        (name, display_name, json.dumps(permissions), system_role),
                    )
        else:
            with self._sqlite_connect() as conn:
                conn.execute(
                    """
                    INSERT INTO app_roles(name, display_name, permissions, system_role, active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                    """,
                    (name, display_name, json.dumps(permissions), int(system_role), now, now),
                )
                conn.commit()
        return RoleRecord(name, display_name, permissions, system_role, True)

    def create_role(
        self,
        *,
        name: str,
        display_name: str,
        permissions: list[str] | tuple[str, ...] | set[str],
    ) -> RoleRecord:
        clean_name = str(name or "").strip().casefold().replace(" ", "_")
        clean_display = str(display_name or "").strip()
        clean_permissions = _clean_permissions(permissions)
        if not ROLE_PATTERN.fullmatch(clean_name):
            raise ValueError("Role names must be 3-64 lowercase letters, numbers, underscores, or hyphens.")
        if not clean_display:
            raise ValueError("A role display name is required.")
        if self.get_role(clean_name):
            raise ValueError("That role already exists.")
        return self._insert_role(clean_name, clean_display, clean_permissions, system_role=False)

    def get_role(self, name: str) -> RoleRecord | None:
        clean_name = str(name or "").strip().casefold()
        if not clean_name:
            return None
        if self.backend == "postgres":
            assert self.database_url
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT name, display_name, permissions, system_role, active FROM app_roles WHERE name=%s",
                        (clean_name,),
                    )
                    row = cur.fetchone()
        else:
            with self._sqlite_connect() as conn:
                row = conn.execute(
                    "SELECT name, display_name, permissions, system_role, active FROM app_roles WHERE name=?",
                    (clean_name,),
                ).fetchone()
        return self._role_from_row(row) if row else None

    def list_roles(self, *, active_only: bool = True) -> list[RoleRecord]:
        if self.backend == "postgres":
            assert self.database_url
            where = "WHERE active=TRUE" if active_only else ""
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT name, display_name, permissions, system_role, active FROM app_roles {where} ORDER BY system_role DESC, display_name"
                    )
                    rows = cur.fetchall()
        else:
            where = "WHERE active=1" if active_only else ""
            with self._sqlite_connect() as conn:
                rows = conn.execute(
                    f"SELECT name, display_name, permissions, system_role, active FROM app_roles {where} ORDER BY system_role DESC, display_name"
                ).fetchall()
        return [self._role_from_row(row) for row in rows]

    def create_user(
        self,
        *,
        username: str,
        password_hash: str,
        role: str,
        created_by: str,
        display_name: str = "",
        email: str = "",
        must_change_password: bool = True,
    ) -> UserRecord:
        clean_username = str(username or "").strip()
        normalized = normalize_username(clean_username)
        clean_role = str(role or "").strip().casefold()
        safe_hash = _validate_password_hash(password_hash)
        if not USERNAME_PATTERN.fullmatch(clean_username):
            raise ValueError("Username must be 3-120 characters using letters, numbers, ., _, or -.")
        role_record = self.get_role(clean_role)
        if not role_record or not role_record.active:
            raise ValueError("Select an active role.")
        if self.get_user(clean_username):
            raise ValueError("That username already exists.")
        user_id = str(uuid4())
        now = utcnow_iso()
        if self.backend == "postgres":
            assert self.database_url
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO app_users(
                            id, username, normalized_username, display_name, email, password_hash,
                            role, active, must_change_password, created_by, updated_by
                        )
                        VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, TRUE, %s, %s, %s)
                        """,
                        (
                            user_id,
                            clean_username,
                            normalized,
                            str(display_name or "").strip(),
                            str(email or "").strip().casefold(),
                            safe_hash,
                            clean_role,
                            must_change_password,
                            created_by,
                            created_by,
                        ),
                    )
        else:
            with self._sqlite_connect() as conn:
                conn.execute(
                    """
                    INSERT INTO app_users(
                        id, username, normalized_username, display_name, email, password_hash,
                        role, active, must_change_password, created_by, updated_by, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        clean_username,
                        normalized,
                        str(display_name or "").strip(),
                        str(email or "").strip().casefold(),
                        safe_hash,
                        clean_role,
                        int(must_change_password),
                        created_by,
                        created_by,
                        now,
                        now,
                    ),
                )
                conn.commit()
        created = self.get_user(clean_username)
        if created is None:
            raise RuntimeError("The user could not be loaded after creation.")
        return created

    def ensure_bootstrap_admin(self, username: str | None, password_hash: str | None) -> UserRecord | None:
        clean_username = str(username or "").strip()
        safe_hash = str(password_hash or "").strip()
        if not clean_username or not safe_hash:
            return None
        existing = self.get_user(clean_username)
        if existing:
            return existing
        try:
            return self.create_user(
                username=clean_username,
                password_hash=safe_hash,
                role="admin",
                created_by="bootstrap-config",
                must_change_password=False,
            )
        except (RuntimeError, ValueError):
            return None

    def get_user(self, username: str) -> UserRecord | None:
        normalized = normalize_username(username)
        if not normalized:
            return None
        if self.backend == "postgres":
            assert self.database_url
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, username, normalized_username, display_name, email, password_hash,
                               role, active, must_change_password, last_login_at, created_at
                        FROM app_users WHERE normalized_username=%s
                        """,
                        (normalized,),
                    )
                    row = cur.fetchone()
        else:
            with self._sqlite_connect() as conn:
                row = conn.execute(
                    """
                    SELECT id, username, normalized_username, display_name, email, password_hash,
                           role, active, must_change_password, last_login_at, created_at
                    FROM app_users WHERE normalized_username=?
                    """,
                    (normalized,),
                ).fetchone()
        return self._user_from_row(row) if row else None

    def list_users(self) -> list[UserRecord]:
        columns = """
            id, username, normalized_username, display_name, email, password_hash,
            role, active, must_change_password, last_login_at, created_at
        """
        if self.backend == "postgres":
            assert self.database_url
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT {columns} FROM app_users ORDER BY username")
                    rows = cur.fetchall()
        else:
            with self._sqlite_connect() as conn:
                rows = conn.execute(f"SELECT {columns} FROM app_users ORDER BY username").fetchall()
        return [self._user_from_row(row) for row in rows]

    def authenticate(self, username: str, password: str) -> UserRecord | None:
        user = self.get_user(username)
        if not user or not user.active or not verify_password(password, user.password_hash):
            return None
        self.record_login(user.id)
        return self.get_user(user.username)

    def record_login(self, user_id: str) -> None:
        self._update_user_timestamp(user_id, "last_login_at", utcnow_iso(), updated_by=None)

    def set_active(self, user_id: str, active: bool, updated_by: str) -> bool:
        return self._update_user_value(user_id, "active", bool(active), updated_by)

    def set_role(self, user_id: str, role: str, updated_by: str) -> bool:
        clean_role = str(role or "").strip().casefold()
        role_record = self.get_role(clean_role)
        if not role_record or not role_record.active:
            raise ValueError("Select an active role.")
        return self._update_user_value(user_id, "role", clean_role, updated_by)

    def reset_password(self, user_id: str, password_hash: str, updated_by: str) -> bool:
        safe_hash = _validate_password_hash(password_hash)
        now = utcnow_iso()
        with self._lock:
            if not self._update_user_value(user_id, "password_hash", safe_hash, updated_by):
                return False
            self._update_user_value(user_id, "must_change_password", True, updated_by)
            self._update_user_timestamp(user_id, "password_changed_at", now, updated_by=updated_by)
        return True

    def change_password(self, user_id: str, password_hash: str) -> bool:
        safe_hash = _validate_password_hash(password_hash)
        user = next((item for item in self.list_users() if item.id == user_id), None)
        if not user or not user.active:
            return False
        with self._lock:
            if not self._update_user_value(user_id, "password_hash", safe_hash, user.username):
                return False
            self._update_user_value(user_id, "must_change_password", False, user.username)
            self._update_user_timestamp(
                user_id,
                "password_changed_at",
                utcnow_iso(),
                updated_by=user.username,
            )
        return True

    def _update_user_value(self, user_id: str, column: str, value: Any, updated_by: str) -> bool:
        allowed = {"active", "password_hash", "must_change_password", "role"}
        if column not in allowed:
            raise ValueError("Unsupported user update.")
        if self.backend == "postgres":
            assert self.database_url
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"UPDATE app_users SET {column}=%s, updated_by=%s, updated_at=now() WHERE id=%s::uuid",
                        (value, updated_by, user_id),
                    )
                    return cur.rowcount == 1
        with self._sqlite_connect() as conn:
            cur = conn.execute(
                f"UPDATE app_users SET {column}=?, updated_by=?, updated_at=? WHERE id=?",
                (int(value) if isinstance(value, bool) else value, updated_by, utcnow_iso(), user_id),
            )
            conn.commit()
            return cur.rowcount == 1

    def _update_user_timestamp(
        self,
        user_id: str,
        column: str,
        value: str,
        *,
        updated_by: str | None,
    ) -> bool:
        if column not in {"last_login_at", "password_changed_at"}:
            raise ValueError("Unsupported timestamp update.")
        if self.backend == "postgres":
            assert self.database_url
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"UPDATE app_users SET {column}=%s::timestamptz, updated_by=COALESCE(%s, updated_by), updated_at=now() WHERE id=%s::uuid",
                        (value, updated_by, user_id),
                    )
                    return cur.rowcount == 1
        with self._sqlite_connect() as conn:
            cur = conn.execute(
                f"UPDATE app_users SET {column}=?, updated_by=COALESCE(?, updated_by), updated_at=? WHERE id=?",
                (value, updated_by, utcnow_iso(), user_id),
            )
            conn.commit()
            return cur.rowcount == 1

    @staticmethod
    def _role_from_row(row: Any) -> RoleRecord:
        raw_permissions = row[2]
        if isinstance(raw_permissions, str):
            raw_permissions = json.loads(raw_permissions)
        return RoleRecord(
            name=str(row[0]),
            display_name=str(row[1]),
            permissions=tuple(str(item) for item in (raw_permissions or [])),
            system_role=bool(row[3]),
            active=bool(row[4]),
        )

    @staticmethod
    def _user_from_row(row: Any) -> UserRecord:
        return UserRecord(
            id=str(row[0]),
            username=str(row[1]),
            normalized_username=str(row[2]),
            display_name=str(row[3] or ""),
            email=str(row[4] or ""),
            password_hash=str(row[5]),
            role=str(row[6]),
            active=bool(row[7]),
            must_change_password=bool(row[8]),
            last_login_at=str(row[9]) if row[9] else None,
            created_at=str(row[10]) if row[10] else None,
        )
