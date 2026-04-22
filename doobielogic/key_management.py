from __future__ import annotations

import hashlib
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

try:
    import psycopg
except Exception:  # pragma: no cover - optional dependency for postgres runtime
    psycopg = None

KEY_TYPE_LICENSE = "license"
KEY_TYPE_API = "api"
KEY_ROLE_SERVICE = "service"
KEY_ROLE_ADMIN = "admin"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _normalize_expiration(expires_at: str | None) -> str | None:
    if not expires_at:
        return None
    safe = str(expires_at).strip()
    if not safe:
        return None
    if len(safe) == 10:
        return f"{safe}T00:00:00+00:00"
    parsed = datetime.fromisoformat(safe.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat()


def _is_expired(expires_at: str | None) -> bool:
    if not expires_at:
        return False
    try:
        parsed = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    except ValueError:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed <= datetime.now(timezone.utc)


def _is_postgres_url(database_url: str | None) -> bool:
    if not database_url:
        return False
    scheme = urlparse(database_url).scheme.lower()
    return scheme in {"postgres", "postgresql"}


@dataclass(frozen=True)
class GeneratedKey:
    record_id: str
    raw_key: str
    key_preview: str


class KeyStore:
    def __init__(self, path: str | Path = "data/key_store.db", *, database_url: str | None = None):
        self.database_url = (database_url or "").strip() or None
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._backend = "postgres" if _is_postgres_url(self.database_url) else "sqlite"
        if self._backend == "postgres" and psycopg is None:
            raise RuntimeError("Postgres database URL configured but psycopg is not installed.")
        self._init_db()
        self._migrate_legacy_sqlite_if_needed()

    def _sqlite_connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _postgres_connect(self):
        assert self.database_url is not None
        assert psycopg is not None
        conn = psycopg.connect(self.database_url)
        conn.autocommit = False
        return conn

    def _init_db(self) -> None:
        if self._backend == "postgres":
            with self._postgres_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS key_records (
                            id TEXT PRIMARY KEY,
                            key_type TEXT NOT NULL CHECK(key_type IN ('license', 'api')),
                            key_hash TEXT NOT NULL UNIQUE,
                            key_preview TEXT NOT NULL,
                            company_name TEXT NOT NULL,
                            label TEXT NOT NULL,
                            tier_or_scope TEXT NOT NULL,
                            key_role TEXT NOT NULL DEFAULT 'service' CHECK(key_role IN ('service', 'admin')),
                            is_bootstrap INTEGER NOT NULL DEFAULT 0,
                            created_at TEXT NOT NULL,
                            expires_at TEXT,
                            is_active INTEGER NOT NULL DEFAULT 1,
                            is_revoked INTEGER NOT NULL DEFAULT 0,
                            trial INTEGER NOT NULL DEFAULT 0,
                            max_users INTEGER,
                            notes TEXT,
                            contact_email TEXT,
                            updated_at TEXT NOT NULL
                        )
                        """
                    )
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_key_records_type ON key_records(key_type)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_key_records_company ON key_records(company_name)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_key_records_created ON key_records(created_at)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_key_records_role ON key_records(key_role)")
                conn.commit()
            return

        with self._sqlite_connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS key_records (
                    id TEXT PRIMARY KEY,
                    key_type TEXT NOT NULL CHECK(key_type IN ('license', 'api')),
                    key_hash TEXT NOT NULL UNIQUE,
                    key_preview TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    label TEXT NOT NULL,
                    tier_or_scope TEXT NOT NULL,
                    key_role TEXT NOT NULL DEFAULT 'service' CHECK(key_role IN ('service', 'admin')),
                    is_bootstrap INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    is_revoked INTEGER NOT NULL DEFAULT 0,
                    trial INTEGER NOT NULL DEFAULT 0,
                    max_users INTEGER,
                    notes TEXT,
                    contact_email TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_key_records_type ON key_records(key_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_key_records_company ON key_records(company_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_key_records_created ON key_records(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_key_records_role ON key_records(key_role)")
            conn.commit()

    def _migrate_legacy_sqlite_if_needed(self) -> None:
        if self._backend != "postgres" or not self.path.exists():
            return
        try:
            with self._postgres_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(1) FROM key_records")
                    existing = int((cur.fetchone() or [0])[0])
                conn.commit()
            if existing > 0:
                return
            with sqlite3.connect(self.path) as legacy:
                legacy.row_factory = sqlite3.Row
                rows = [dict(row) for row in legacy.execute("SELECT * FROM key_records").fetchall()]
        except Exception:
            return
        if not rows:
            return
        with self._lock:
            with self._postgres_connect() as conn:
                with conn.cursor() as cur:
                    for row in rows:
                        cur.execute(
                            """
                            INSERT INTO key_records (
                                id, key_type, key_hash, key_preview, company_name, label, tier_or_scope, key_role, is_bootstrap, created_at,
                                expires_at, is_active, is_revoked, trial, max_users, notes, contact_email, updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO NOTHING
                            """,
                            (
                                row["id"],
                                row["key_type"],
                                row["key_hash"],
                                row["key_preview"],
                                row["company_name"],
                                row["label"],
                                row["tier_or_scope"],
                                row.get("key_role") or KEY_ROLE_SERVICE,
                                int(row.get("is_bootstrap") or 0),
                                row["created_at"],
                                row.get("expires_at"),
                                int(row.get("is_active") or 1),
                                int(row.get("is_revoked") or 0),
                                int(row.get("trial") or 0),
                                row.get("max_users"),
                                row.get("notes"),
                                row.get("contact_email"),
                                row.get("updated_at") or row["created_at"],
                            ),
                        )
                conn.commit()

    def diagnostic(self) -> dict[str, str]:
        if self._backend == "postgres":
            return {"backend": "postgres", "database_url": "configured"}
        return {"backend": "local_sqlite", "path": str(self.path)}

    def generate_license_key(self) -> str:
        return f"DLB-LIC-{secrets.token_urlsafe(24)}"

    def generate_api_key(self) -> str:
        return f"DLB-API-{secrets.token_urlsafe(32)}"

    def generate_admin_key(self) -> str:
        return f"DLB-ADM-{secrets.token_urlsafe(32)}"

    def save_key_record(
        self,
        *,
        key_type: str,
        raw_key: str,
        company_name: str,
        label: str,
        tier_or_scope: str,
        key_role: str = KEY_ROLE_SERVICE,
        is_bootstrap: bool = False,
        expires_at: str | None = None,
        trial: bool = False,
        max_users: int | None = None,
        notes: str = "",
        contact_email: str | None = None,
    ) -> str:
        now = _utcnow_iso()
        record_id = f"key_{uuid4().hex}"
        expires_iso = _normalize_expiration(expires_at)
        key_digest = hash_key(raw_key)
        key_preview = raw_key[-8:]
        args = (
            record_id,
            key_type,
            key_digest,
            key_preview,
            company_name.strip(),
            label.strip(),
            tier_or_scope.strip(),
            key_role,
            1 if is_bootstrap else 0,
            now,
            expires_iso,
            1,
            0,
            1 if trial else 0,
            max_users,
            notes.strip(),
            (contact_email or "").strip() or None,
            now,
        )
        with self._lock:
            if self._backend == "postgres":
                with self._postgres_connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO key_records (
                                id, key_type, key_hash, key_preview, company_name, label, tier_or_scope, key_role, is_bootstrap, created_at,
                                expires_at, is_active, is_revoked, trial, max_users, notes, contact_email, updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            args,
                        )
                    conn.commit()
            else:
                with self._sqlite_connect() as conn:
                    conn.execute(
                        """
                        INSERT INTO key_records (
                            id, key_type, key_hash, key_preview, company_name, label, tier_or_scope, key_role, is_bootstrap, created_at,
                            expires_at, is_active, is_revoked, trial, max_users, notes, contact_email, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        args,
                    )
                    conn.commit()
        return record_id

    def create_license_key(self, *, company_name: str, email: str | None, tier: str, expiration_date: date | None, max_users: int | None, trial: bool, notes: str) -> GeneratedKey:
        raw_key = self.generate_license_key()
        record_id = self.save_key_record(
            key_type=KEY_TYPE_LICENSE,
            raw_key=raw_key,
            company_name=company_name,
            label=f"{company_name.strip()} license",
            tier_or_scope=tier,
            key_role=KEY_ROLE_SERVICE,
            expires_at=expiration_date.isoformat() if expiration_date else None,
            trial=trial,
            max_users=max_users,
            notes=notes,
            contact_email=email,
        )
        return GeneratedKey(record_id=record_id, raw_key=raw_key, key_preview=raw_key[-8:])

    def create_api_key(self, *, company_name: str, label: str, scope: str, expiration_date: date | None, notes: str) -> GeneratedKey:
        raw_key = self.generate_api_key()
        record_id = self.save_key_record(
            key_type=KEY_TYPE_API,
            raw_key=raw_key,
            company_name=company_name,
            label=label,
            tier_or_scope=scope,
            key_role=KEY_ROLE_SERVICE,
            expires_at=expiration_date.isoformat() if expiration_date else None,
            notes=notes,
        )
        return GeneratedKey(record_id=record_id, raw_key=raw_key, key_preview=raw_key[-8:])

    def create_admin_api_key(self, *, label: str, notes: str = "", expiration_date: date | None = None, is_bootstrap: bool = False) -> GeneratedKey:
        raw_key = self.generate_admin_key()
        record_id = self.save_key_record(
            key_type=KEY_TYPE_API,
            raw_key=raw_key,
            company_name="DoobieLogic Admin",
            label=label,
            tier_or_scope="admin",
            key_role=KEY_ROLE_ADMIN,
            is_bootstrap=is_bootstrap,
            expires_at=expiration_date.isoformat() if expiration_date else None,
            notes=notes,
        )
        return GeneratedKey(record_id=record_id, raw_key=raw_key, key_preview=raw_key[-8:])

    def _fetchone_dict(self, sql_sqlite: str, sql_pg: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        if self._backend == "postgres":
            with self._postgres_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql_pg, params)
                    row = cur.fetchone()
                    if not row:
                        return None
                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, row))
        with self._sqlite_connect() as conn:
            row = conn.execute(sql_sqlite, params).fetchone()
            return dict(row) if row else None

    def has_active_admin_key(self) -> bool:
        row = self._fetchone_dict(
            """
            SELECT 1 FROM key_records
            WHERE key_type = ? AND key_role = ? AND is_active = 1 AND is_revoked = 0
            LIMIT 1
            """,
            """
            SELECT 1 FROM key_records
            WHERE key_type = %s AND key_role = %s AND is_active = 1 AND is_revoked = 0
            LIMIT 1
            """,
            (KEY_TYPE_API, KEY_ROLE_ADMIN),
        )
        return bool(row)

    def load_key_records(self, key_type: str | None = None, search: str | None = None, key_role: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM key_records"
        filters: list[str] = []
        params: list[Any] = []
        binder = "%s" if self._backend == "postgres" else "?"
        if key_type:
            filters.append(f"key_type = {binder}")
            params.append(key_type)
        if key_role:
            filters.append(f"key_role = {binder}")
            params.append(key_role)
        if search:
            filters.append(
                f"(LOWER(company_name) LIKE {binder} OR LOWER(label) LIKE {binder} OR LOWER(tier_or_scope) LIKE {binder} OR LOWER(notes) LIKE {binder})"
            )
            pattern = f"%{search.lower()}%"
            params.extend([pattern, pattern, pattern, pattern])
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY created_at DESC"

        if self._backend == "postgres":
            with self._postgres_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    rows = cur.fetchall()
                    cols = [d[0] for d in cur.description]
                    return [dict(zip(cols, row)) for row in rows]

        with self._sqlite_connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def revoke_key(self, record_id: str) -> bool:
        return self._update_flags(record_id, is_revoked=1, is_active=0)

    def toggle_key_status(self, record_id: str, is_active: bool) -> bool:
        return self._update_flags(record_id, is_active=1 if is_active else 0)

    def _update_flags(self, record_id: str, *, is_active: int | None = None, is_revoked: int | None = None) -> bool:
        updates: list[str] = []
        params: list[Any] = []
        binder = "%s" if self._backend == "postgres" else "?"
        if is_active is not None:
            updates.append(f"is_active = {binder}")
            params.append(is_active)
        if is_revoked is not None:
            updates.append(f"is_revoked = {binder}")
            params.append(is_revoked)
        updates.append(f"updated_at = {binder}")
        params.append(_utcnow_iso())
        params.append(record_id)
        sql = f"UPDATE key_records SET {', '.join(updates)} WHERE id = {binder}"
        with self._lock:
            if self._backend == "postgres":
                with self._postgres_connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql, tuple(params))
                        changed = cur.rowcount > 0
                    conn.commit()
                    return changed
            with self._sqlite_connect() as conn:
                result = conn.execute(sql, tuple(params))
                conn.commit()
                return result.rowcount > 0

    def update_key_metadata(self, record_id: str, *, expires_at: str | None = None, notes: str | None = None, tier_or_scope: str | None = None, label: str | None = None, max_users: int | None = None, trial: bool | None = None) -> bool:
        updates: list[str] = []
        params: list[Any] = []
        binder = "%s" if self._backend == "postgres" else "?"
        if expires_at is not None:
            updates.append(f"expires_at = {binder}")
            params.append(_normalize_expiration(expires_at))
        if notes is not None:
            updates.append(f"notes = {binder}")
            params.append(notes.strip())
        if tier_or_scope is not None:
            updates.append(f"tier_or_scope = {binder}")
            params.append(tier_or_scope.strip())
        if label is not None:
            updates.append(f"label = {binder}")
            params.append(label.strip())
        if max_users is not None:
            updates.append(f"max_users = {binder}")
            params.append(max_users)
        if trial is not None:
            updates.append(f"trial = {binder}")
            params.append(1 if trial else 0)
        if not updates:
            return False
        updates.append(f"updated_at = {binder}")
        params.append(_utcnow_iso())
        params.append(record_id)
        sql = f"UPDATE key_records SET {', '.join(updates)} WHERE id = {binder}"
        with self._lock:
            if self._backend == "postgres":
                with self._postgres_connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql, tuple(params))
                        changed = cur.rowcount > 0
                    conn.commit()
                    return changed
            with self._sqlite_connect() as conn:
                result = conn.execute(sql, tuple(params))
                conn.commit()
                return result.rowcount > 0

    def validate_api_key(self, input_key: str, *, expected_role: str | None = KEY_ROLE_SERVICE) -> dict[str, Any]:
        safe_key = (input_key or "").strip()
        if not safe_key:
            return {"valid": False, "reason": "missing_key", "company": None, "scope": None, "expires_at": None, "expires": None, "key_role": None, "diagnostic": self.diagnostic()}

        key_digest = hash_key(safe_key)
        record = self._fetchone_dict(
            "SELECT * FROM key_records WHERE key_type = ? AND key_hash = ?",
            "SELECT * FROM key_records WHERE key_type = %s AND key_hash = %s",
            (KEY_TYPE_API, key_digest),
        )
        if not record:
            return {"valid": False, "reason": "not_found", "company": None, "scope": None, "expires_at": None, "expires": None, "key_role": None, "diagnostic": self.diagnostic()}

        expires_at = record.get("expires_at")
        key_role = str(record.get("key_role") or KEY_ROLE_SERVICE)

        if expected_role and key_role != expected_role:
            return {"valid": False, "reason": "wrong_key_type", "company": record["company_name"], "scope": record["tier_or_scope"], "expires_at": expires_at, "expires": expires_at, "key_role": key_role, "diagnostic": self.diagnostic()}
        if int(record.get("is_revoked") or 0) == 1:
            return {"valid": False, "reason": "revoked", "company": record["company_name"], "scope": record["tier_or_scope"], "expires_at": expires_at, "expires": expires_at, "key_role": key_role, "diagnostic": self.diagnostic()}
        if int(record.get("is_active") or 0) != 1:
            return {"valid": False, "reason": "disabled", "company": record["company_name"], "scope": record["tier_or_scope"], "expires_at": expires_at, "expires": expires_at, "key_role": key_role, "diagnostic": self.diagnostic()}
        if _is_expired(expires_at):
            self.toggle_key_status(record["id"], is_active=False)
            return {"valid": False, "reason": "expired", "company": record["company_name"], "scope": record["tier_or_scope"], "expires_at": expires_at, "expires": expires_at, "key_role": key_role, "diagnostic": self.diagnostic()}

        return {
            "valid": True,
            "reason": "",
            "company": record["company_name"],
            "scope": record["tier_or_scope"],
            "expires_at": expires_at,
            "expires": expires_at,
            "key_id": record["id"],
            "label": record["label"],
            "permissions": [scope.strip() for scope in str(record["tier_or_scope"]).split(",") if scope.strip()],
            "key_role": key_role,
            "is_bootstrap": bool(int(record.get("is_bootstrap") or 0)),
            "diagnostic": self.diagnostic(),
        }

    def validate_admin_key(self, input_key: str) -> dict[str, Any]:
        return self.validate_api_key(input_key, expected_role=KEY_ROLE_ADMIN)
