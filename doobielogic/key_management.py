from __future__ import annotations

import hashlib
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

KEY_TYPE_LICENSE = "license"
KEY_TYPE_API = "api"


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
    parsed = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed <= datetime.now(timezone.utc)


@dataclass(frozen=True)
class GeneratedKey:
    record_id: str
    raw_key: str
    key_preview: str


class KeyStore:
    def __init__(self, path: str | Path = "data/key_store.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
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
            conn.commit()

    def generate_license_key(self) -> str:
        return f"DLB-LIC-{secrets.token_urlsafe(24)}"

    def generate_api_key(self) -> str:
        return f"DLB-API-{secrets.token_urlsafe(32)}"

    def save_key_record(
        self,
        *,
        key_type: str,
        raw_key: str,
        company_name: str,
        label: str,
        tier_or_scope: str,
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
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO key_records (
                        id, key_type, key_hash, key_preview, company_name, label, tier_or_scope, created_at,
                        expires_at, is_active, is_revoked, trial, max_users, notes, contact_email, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        key_type,
                        key_digest,
                        key_preview,
                        company_name.strip(),
                        label.strip(),
                        tier_or_scope.strip(),
                        now,
                        expires_iso,
                        1,
                        0,
                        1 if trial else 0,
                        max_users,
                        notes.strip(),
                        (contact_email or "").strip() or None,
                        now,
                    ),
                )
                conn.commit()
        return record_id

    def create_license_key(
        self,
        *,
        company_name: str,
        email: str | None,
        tier: str,
        expiration_date: date | None,
        max_users: int | None,
        trial: bool,
        notes: str,
    ) -> GeneratedKey:
        raw_key = self.generate_license_key()
        record_id = self.save_key_record(
            key_type=KEY_TYPE_LICENSE,
            raw_key=raw_key,
            company_name=company_name,
            label=f"{company_name.strip()} license",
            tier_or_scope=tier,
            expires_at=expiration_date.isoformat() if expiration_date else None,
            trial=trial,
            max_users=max_users,
            notes=notes,
            contact_email=email,
        )
        return GeneratedKey(record_id=record_id, raw_key=raw_key, key_preview=raw_key[-8:])

    def create_api_key(
        self,
        *,
        company_name: str,
        label: str,
        scope: str,
        expiration_date: date | None,
        notes: str,
    ) -> GeneratedKey:
        raw_key = self.generate_api_key()
        record_id = self.save_key_record(
            key_type=KEY_TYPE_API,
            raw_key=raw_key,
            company_name=company_name,
            label=label,
            tier_or_scope=scope,
            expires_at=expiration_date.isoformat() if expiration_date else None,
            notes=notes,
        )
        return GeneratedKey(record_id=record_id, raw_key=raw_key, key_preview=raw_key[-8:])

    def load_key_records(self, key_type: str | None = None, search: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM key_records"
        filters: list[str] = []
        params: list[Any] = []
        if key_type:
            filters.append("key_type = ?")
            params.append(key_type)
        if search:
            filters.append("(LOWER(company_name) LIKE ? OR LOWER(label) LIKE ? OR LOWER(tier_or_scope) LIKE ? OR LOWER(notes) LIKE ?)")
            pattern = f"%{search.lower()}%"
            params.extend([pattern, pattern, pattern, pattern])
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY created_at DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def revoke_key(self, record_id: str) -> bool:
        return self._update_flags(record_id, is_revoked=1, is_active=0)

    def toggle_key_status(self, record_id: str, is_active: bool) -> bool:
        return self._update_flags(record_id, is_active=1 if is_active else 0)

    def _update_flags(self, record_id: str, *, is_active: int | None = None, is_revoked: int | None = None) -> bool:
        updates: list[str] = []
        params: list[Any] = []
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)
        if is_revoked is not None:
            updates.append("is_revoked = ?")
            params.append(is_revoked)
        updates.append("updated_at = ?")
        params.append(_utcnow_iso())
        params.append(record_id)
        sql = f"UPDATE key_records SET {', '.join(updates)} WHERE id = ?"
        with self._lock:
            with self._connect() as conn:
                result = conn.execute(sql, params)
                conn.commit()
                return result.rowcount > 0

    def update_key_metadata(
        self,
        record_id: str,
        *,
        expires_at: str | None = None,
        notes: str | None = None,
        tier_or_scope: str | None = None,
        label: str | None = None,
        max_users: int | None = None,
        trial: bool | None = None,
    ) -> bool:
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
        params.append(_utcnow_iso())
        params.append(record_id)
        sql = f"UPDATE key_records SET {', '.join(updates)} WHERE id = ?"
        with self._lock:
            with self._connect() as conn:
                result = conn.execute(sql, params)
                conn.commit()
                return result.rowcount > 0

    def validate_api_key(self, input_key: str) -> dict[str, Any]:
        safe_key = (input_key or "").strip()
        if not safe_key:
            return {"valid": False, "reason": "missing_key", "company": None, "scope": None, "expires_at": None, "expires": None}
        key_digest = hash_key(safe_key)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM key_records WHERE key_type = ? AND key_hash = ?",
                (KEY_TYPE_API, key_digest),
            ).fetchone()
        if not row:
            return {"valid": False, "reason": "not_found", "company": None, "scope": None, "expires_at": None, "expires": None}

        record = dict(row)
        expires_at = record.get("expires_at")
        if int(record.get("is_revoked") or 0) == 1:
            return {"valid": False, "reason": "revoked", "company": record["company_name"], "scope": record["tier_or_scope"], "expires_at": expires_at, "expires": expires_at}
        if int(record.get("is_active") or 0) != 1:
            return {"valid": False, "reason": "disabled", "company": record["company_name"], "scope": record["tier_or_scope"], "expires_at": expires_at, "expires": expires_at}
        if _is_expired(expires_at):
            self.toggle_key_status(record["id"], is_active=False)
            return {"valid": False, "reason": "expired", "company": record["company_name"], "scope": record["tier_or_scope"], "expires_at": expires_at, "expires": expires_at}

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
        }
