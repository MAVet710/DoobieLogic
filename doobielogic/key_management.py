from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from doobielogic.postgres_persistence import (
    append_audit_event,
    generate_prefixed_secret,
    hash_secret,
    init_postgres_schema,
    is_postgres_url,
    key_preview,
    postgres_connection,
    utcnow_iso,
)

KEY_TYPE_LICENSE = "license"
KEY_TYPE_API = "api"
KEY_ROLE_SERVICE = "service"
KEY_ROLE_ADMIN = "admin"


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
        self._backend = "postgres" if is_postgres_url(self.database_url) else "sqlite"
        self._init_db()
        self._migrate_legacy_sqlite_if_needed()

    def _sqlite_connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        if self._backend == "postgres":
            assert self.database_url is not None
            init_postgres_schema(self.database_url)
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
            conn.commit()

    def _migrate_legacy_sqlite_if_needed(self) -> None:
        if self._backend != "postgres" or not self.path.exists():
            return
        try:
            with self._sqlite_connect() as legacy:
                rows = [dict(row) for row in legacy.execute("SELECT * FROM key_records").fetchall()]
        except Exception:
            return
        if not rows:
            return
        assert self.database_url is not None
        with self._lock:
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    for row in rows:
                        key_type = "admin" if (row.get("key_role") or KEY_ROLE_SERVICE) == KEY_ROLE_ADMIN else "service"
                        cur.execute(
                            """
                            INSERT INTO api_keys(id, key_type, key_hash, key_preview, key_prefix, label, scope, status, created_by, notes, issued_at, expires_at)
                            VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz)
                            ON CONFLICT (key_hash) DO NOTHING
                            """,
                            (
                                str(uuid4()),
                                key_type,
                                row["key_hash"],
                                row["key_preview"],
                                "DLB-ADM" if key_type == "admin" else "DLB-SVC",
                                row.get("label") or "legacy",
                                row.get("tier_or_scope") or ("admin" if key_type == "admin" else "buyer_dashboard"),
                                "revoked" if int(row.get("is_revoked") or 0) == 1 else ("active" if int(row.get("is_active") or 1) == 1 else "disabled"),
                                "legacy_migration",
                                row.get("notes"),
                                row.get("created_at") or utcnow_iso(),
                                row.get("expires_at"),
                            ),
                        )

    def diagnostic(self) -> dict[str, str]:
        if self._backend == "postgres":
            return {"backend": "postgres", "database_url": "configured"}
        return {"backend": "local_sqlite", "path": str(self.path)}

    def generate_api_key(self) -> str:
        return generate_prefixed_secret("DLB-SVC", token_bytes=32)

    def generate_admin_key(self) -> str:
        return generate_prefixed_secret("DLB-ADM", token_bytes=32)

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
        now = utcnow_iso()
        record_id = str(uuid4()) if self._backend == "postgres" else f"key_{uuid4().hex}"
        expires_iso = _normalize_expiration(expires_at)
        key_digest = hash_secret(raw_key)
        preview = key_preview(raw_key)
        with self._lock:
            if self._backend == "postgres":
                assert self.database_url is not None
                key_db_type = "admin" if key_role == KEY_ROLE_ADMIN else "service"
                key_prefix = "DLB-ADM" if key_db_type == "admin" else "DLB-SVC"
                status = "active"
                with postgres_connection(self.database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO api_keys(id, key_type, key_hash, key_preview, key_prefix, label, scope, status, created_by, notes, issued_at, expires_at)
                            VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz)
                            """,
                            (
                                record_id,
                                key_db_type,
                                key_digest,
                                preview,
                                key_prefix,
                                label.strip(),
                                tier_or_scope.strip(),
                                status,
                                "bootstrap" if is_bootstrap else "admin_ui",
                                notes.strip() or None,
                                now,
                                expires_iso,
                            ),
                        )
                append_audit_event(
                    self.database_url,
                    event_type="api_key_created",
                    actor_type="admin_user",
                    actor_identifier=None,
                    target_type="api_key",
                    target_id=record_id,
                    event_data={"key_type": key_db_type, "scope": tier_or_scope, "label": label},
                )
                return record_id

            args = (
                record_id,
                key_type,
                key_digest,
                preview,
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

    def has_active_admin_key(self) -> bool:
        if self._backend == "postgres":
            assert self.database_url is not None
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM api_keys WHERE key_type='admin' AND status='active' LIMIT 1")
                    return bool(cur.fetchone())
        with self._sqlite_connect() as conn:
            row = conn.execute("SELECT 1 FROM key_records WHERE key_type='api' AND key_role='admin' AND is_active=1 AND is_revoked=0 LIMIT 1").fetchone()
        return bool(row)

    def load_key_records(self, key_type: str | None = None, search: str | None = None, key_role: str | None = None) -> list[dict[str, Any]]:
        if self._backend == "postgres":
            assert self.database_url is not None
            clauses: list[str] = []
            params: list[Any] = []
            if key_role in {KEY_ROLE_SERVICE, KEY_ROLE_ADMIN}:
                clauses.append("key_type = %s")
                params.append("admin" if key_role == KEY_ROLE_ADMIN else "service")
            if search:
                clauses.append("(LOWER(label) LIKE %s OR LOWER(scope) LIKE %s OR LOWER(COALESCE(notes,'')) LIKE %s)")
                pattern = f"%{search.lower()}%"
                params.extend([pattern, pattern, pattern])
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT id, key_type, key_preview, key_prefix, label, scope, status, created_by, notes, issued_at, expires_at FROM api_keys {where} ORDER BY created_at DESC",
                        tuple(params),
                    )
                    rows = cur.fetchall()
            mapped: list[dict[str, Any]] = []
            for row in rows:
                mapped.append(
                    {
                        "id": str(row[0]),
                        "key_type": "api",
                        "key_role": KEY_ROLE_ADMIN if row[1] == "admin" else KEY_ROLE_SERVICE,
                        "key_preview": row[2],
                        "key_prefix": row[3],
                        "company_name": "DoobieLogic Admin" if row[1] == "admin" else "Service Client",
                        "label": row[4],
                        "tier_or_scope": row[5],
                        "is_active": 1 if row[6] == "active" else 0,
                        "is_revoked": 1 if row[6] == "revoked" else 0,
                        "is_bootstrap": 1 if (row[7] == "bootstrap") else 0,
                        "notes": row[8],
                        "created_at": str(row[9]),
                        "expires_at": str(row[10]) if row[10] else None,
                        "updated_at": str(row[9]),
                    }
                )
            return mapped

        query = "SELECT * FROM key_records"
        filters: list[str] = []
        params: list[Any] = []
        if key_type:
            filters.append("key_type = ?")
            params.append(key_type)
        if key_role:
            filters.append("key_role = ?")
            params.append(key_role)
        if search:
            filters.append("(LOWER(company_name) LIKE ? OR LOWER(label) LIKE ? OR LOWER(tier_or_scope) LIKE ? OR LOWER(notes) LIKE ?)")
            pattern = f"%{search.lower()}%"
            params.extend([pattern, pattern, pattern, pattern])
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY created_at DESC"
        with self._sqlite_connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def revoke_key(self, record_id: str) -> bool:
        return self._update_status(record_id, status="revoked")

    def toggle_key_status(self, record_id: str, is_active: bool) -> bool:
        return self._update_status(record_id, status="active" if is_active else "disabled")

    def _update_status(self, record_id: str, *, status: str) -> bool:
        with self._lock:
            if self._backend == "postgres":
                assert self.database_url is not None
                with postgres_connection(self.database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE api_keys SET status=%s, revoked_at=CASE WHEN %s='revoked' THEN now() ELSE revoked_at END WHERE id=%s::uuid",
                            (status, status, record_id),
                        )
                        changed = cur.rowcount > 0
                return changed
            with self._sqlite_connect() as conn:
                if status == "revoked":
                    result = conn.execute("UPDATE key_records SET is_revoked=1, is_active=0, updated_at=? WHERE id=?", (utcnow_iso(), record_id))
                else:
                    result = conn.execute("UPDATE key_records SET is_active=?, updated_at=? WHERE id=?", (1 if status == "active" else 0, utcnow_iso(), record_id))
                conn.commit()
                return result.rowcount > 0

    def update_key_metadata(self, record_id: str, *, expires_at: str | None = None, notes: str | None = None, tier_or_scope: str | None = None, label: str | None = None, max_users: int | None = None, trial: bool | None = None) -> bool:
        with self._lock:
            if self._backend == "postgres":
                assert self.database_url is not None
                updates: list[str] = []
                params: list[Any] = []
                if expires_at is not None:
                    updates.append("expires_at=%s::timestamptz")
                    params.append(_normalize_expiration(expires_at))
                if notes is not None:
                    updates.append("notes=%s")
                    params.append(notes.strip())
                if tier_or_scope is not None:
                    updates.append("scope=%s")
                    params.append(tier_or_scope.strip())
                if label is not None:
                    updates.append("label=%s")
                    params.append(label.strip())
                if not updates:
                    return False
                params.append(record_id)
                with postgres_connection(self.database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(f"UPDATE api_keys SET {', '.join(updates)} WHERE id=%s::uuid", tuple(params))
                        return cur.rowcount > 0

            updates: list[str] = []
            params: list[Any] = []
            if expires_at is not None:
                updates.append("expires_at = ?")
                params.append(_normalize_expiration(expires_at))
            if notes is not None:
                updates.append("notes = ?")
                params.append(notes.strip())
            if tier_or_scope is not None:
                updates.append("tier_or_scope = ?")
                params.append(tier_or_scope.strip())
            if label is not None:
                updates.append("label = ?")
                params.append(label.strip())
            if max_users is not None:
                updates.append("max_users = ?")
                params.append(max_users)
            if trial is not None:
                updates.append("trial = ?")
                params.append(1 if trial else 0)
            if not updates:
                return False
            updates.append("updated_at = ?")
            params.append(utcnow_iso())
            params.append(record_id)
            with self._sqlite_connect() as conn:
                result = conn.execute(f"UPDATE key_records SET {', '.join(updates)} WHERE id = ?", tuple(params))
                conn.commit()
                return result.rowcount > 0

    def _validate_pg_key(self, input_key: str, expected_role: str | None) -> dict[str, Any]:
        assert self.database_url is not None
        key_hash = hash_secret(input_key)
        with postgres_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, key_type, label, scope, status, expires_at, created_by FROM api_keys WHERE key_hash=%s",
                    (key_hash,),
                )
                row = cur.fetchone()
        if not row:
            return {"valid": False, "reason": "not_found", "company": None, "scope": None, "expires_at": None, "expires": None, "key_role": None, "diagnostic": self.diagnostic()}
        key_role = KEY_ROLE_ADMIN if row[1] == "admin" else KEY_ROLE_SERVICE
        expires_at = str(row[5]) if row[5] else None
        status = str(row[4]).lower()
        if expected_role and key_role != expected_role:
            return {"valid": False, "reason": "wrong_key_type", "company": "DoobieLogic", "scope": row[3], "expires_at": expires_at, "expires": expires_at, "key_role": key_role, "diagnostic": self.diagnostic()}
        if status == "revoked":
            return {"valid": False, "reason": "revoked", "company": "DoobieLogic", "scope": row[3], "expires_at": expires_at, "expires": expires_at, "key_role": key_role, "diagnostic": self.diagnostic()}
        if status == "disabled":
            return {"valid": False, "reason": "disabled", "company": "DoobieLogic", "scope": row[3], "expires_at": expires_at, "expires": expires_at, "key_role": key_role, "diagnostic": self.diagnostic()}
        if status == "expired" or _is_expired(expires_at):
            self._update_status(str(row[0]), status="expired")
            return {"valid": False, "reason": "expired", "company": "DoobieLogic", "scope": row[3], "expires_at": expires_at, "expires": expires_at, "key_role": key_role, "diagnostic": self.diagnostic()}
        return {
            "valid": True,
            "reason": "",
            "company": "DoobieLogic",
            "scope": row[3],
            "expires_at": expires_at,
            "expires": expires_at,
            "key_id": str(row[0]),
            "label": row[2],
            "permissions": [scope.strip() for scope in str(row[3]).split(",") if scope.strip()],
            "key_role": key_role,
            "is_bootstrap": bool(row[6] == "bootstrap"),
            "diagnostic": self.diagnostic(),
        }

    def validate_api_key(self, input_key: str, *, expected_role: str | None = KEY_ROLE_SERVICE) -> dict[str, Any]:
        safe_key = (input_key or "").strip()
        if not safe_key:
            return {"valid": False, "reason": "missing_key", "company": None, "scope": None, "expires_at": None, "expires": None, "key_role": None, "diagnostic": self.diagnostic()}

        if self._backend == "postgres":
            return self._validate_pg_key(safe_key, expected_role)

        key_digest = hash_secret(safe_key)
        with self._sqlite_connect() as conn:
            row = conn.execute("SELECT * FROM key_records WHERE key_type = ? AND key_hash = ?", (KEY_TYPE_API, key_digest)).fetchone()
        if not row:
            return {"valid": False, "reason": "not_found", "company": None, "scope": None, "expires_at": None, "expires": None, "key_role": None, "diagnostic": self.diagnostic()}
        record = dict(row)
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
