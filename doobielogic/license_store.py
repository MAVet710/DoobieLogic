from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from doobielogic.license_models import ALLOWED_PLAN_TYPES, Customer, License
from doobielogic.postgres_persistence import (
    append_audit_event,
    generate_prefixed_secret,
    hash_secret,
    init_postgres_schema,
    is_postgres_url,
    key_preview,
    maybe_masked_key,
    postgres_connection,
    utcnow_iso,
)

PLAN_FEATURES: dict[str, dict[str, bool]] = {
    "trial": {"buyer_module": True, "extraction_module": False, "ai_support": True, "admin_exports": False},
    "standard": {"buyer_module": True, "extraction_module": True, "ai_support": True, "admin_exports": False},
    "premium": {"buyer_module": True, "extraction_module": True, "ai_support": True, "admin_exports": True},
    "enterprise": {"buyer_module": True, "extraction_module": True, "ai_support": True, "admin_exports": True},
}

LICENSE_PREFIX = "DLB-LIC"


class LicenseStore:
    def __init__(self, path: str | Path = "data/license_store.json", *, database_url: str | None = None):
        self.path = Path(path)
        self.database_url = (database_url or "").strip() or None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.sqlite_path = self.path.with_suffix(".db")
        self._lock = Lock()
        self._backend = "postgres" if is_postgres_url(self.database_url) else "sqlite"
        self._legacy_migration: dict[str, int | bool] = {"attempted": False, "imported_customers": 0, "imported_licenses": 0, "skipped_licenses": 0}
        self._init_db()
        self._migrate_legacy_sqlite_if_needed()
        self._migrate_legacy_json_if_needed()

    def _sqlite_connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        if self._backend == "postgres":
            assert self.database_url is not None
            init_postgres_schema(self.database_url)
            return

        ddl = [
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                contact_email TEXT NOT NULL,
                created_at TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS licenses (
                license_key TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                plan_type TEXT NOT NULL,
                status TEXT NOT NULL,
                issued_at TEXT NOT NULL,
                expires_at TEXT,
                last_validated_at TEXT,
                reset_count INTEGER NOT NULL DEFAULT 0,
                revoked_reason TEXT,
                FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
            )
            """,
        ]
        with self._sqlite_connect() as conn:
            for statement in ddl:
                conn.execute(statement)
            conn.commit()

    def _table_count(self, table_name: str) -> int:
        if self._backend == "postgres":
            assert self.database_url is not None
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(1) FROM {table_name}")
                    row = cur.fetchone()
            return int((row or [0])[0])
        with self._sqlite_connect() as conn:
            row = conn.execute(f"SELECT COUNT(1) FROM {table_name}").fetchone()
        return int((row or [0])[0])

    def _migrate_legacy_json_if_needed(self) -> None:
        if not self.path.exists() or self._backend != "postgres":
            return
        try:
            if self._table_count("customers") > 0 or self._table_count("licenses") > 0:
                return
            with self.path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            return

        customers = [Customer.from_dict(row).to_dict() for row in payload.get("customers", [])]
        licenses = [License.from_dict(row).to_dict() for row in payload.get("licenses", [])]
        if not customers and not licenses:
            return

        with self._lock:
            assert self.database_url is not None
            with postgres_connection(self.database_url) as conn:
                customer_map: dict[str, str] = {}
                with conn.cursor() as cur:
                    for row in customers:
                        cur.execute(
                            """
                            INSERT INTO customers(company_name, contact_name, contact_email, notes, status)
                            VALUES (%s, %s, %s, %s, %s)
                            RETURNING id
                            """,
                            (row["company_name"], row.get("contact_name"), row.get("contact_email"), row.get("notes"), "active"),
                        )
                        customer_map[row["customer_id"]] = str(cur.fetchone()[0])
                        self._legacy_migration["imported_customers"] = int(self._legacy_migration["imported_customers"]) + 1

                    for row in licenses:
                        raw_key = str(row.get("license_key") or "").strip()
                        if not raw_key or row.get("customer_id") not in customer_map:
                            continue
                        cur.execute(
                            """
                            INSERT INTO licenses(customer_id, license_key_hash, license_key_preview, license_key_prefix, plan_code, status, issued_at, expires_at, notes)
                            VALUES (%s, %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz, %s)
                            ON CONFLICT (license_key_hash) DO NOTHING
                            """,
                            (
                                customer_map[row["customer_id"]],
                                hash_secret(raw_key),
                                key_preview(raw_key),
                                LICENSE_PREFIX,
                                row.get("plan_type") or "trial",
                                row.get("status") or "active",
                                row.get("issued_at") or utcnow_iso(),
                                row.get("expires_at"),
                                row.get("revoked_reason"),
                            ),
                        )
                        if cur.rowcount > 0:
                            self._legacy_migration["imported_licenses"] = int(self._legacy_migration["imported_licenses"]) + 1
                        else:
                            self._legacy_migration["skipped_licenses"] = int(self._legacy_migration["skipped_licenses"]) + 1

    def _migrate_legacy_sqlite_if_needed(self) -> None:
        if self._backend != "postgres" or not self.sqlite_path.exists():
            return
        self._legacy_migration["attempted"] = True
        try:
            with self._sqlite_connect() as legacy:
                customer_rows = [dict(row) for row in legacy.execute("SELECT * FROM customers").fetchall()]
                license_rows = [dict(row) for row in legacy.execute("SELECT * FROM licenses").fetchall()]
        except Exception:
            return

        if not customer_rows and not license_rows:
            return

        assert self.database_url is not None
        with self._lock:
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    customer_map: dict[str, str] = {}
                    for row in customer_rows:
                        cur.execute(
                            """
                            INSERT INTO customers(company_name, contact_name, contact_email, notes, status)
                            VALUES (%s, %s, %s, %s, %s)
                            RETURNING id
                            """,
                            (
                                row.get("company_name"),
                                row.get("contact_name"),
                                row.get("contact_email"),
                                row.get("notes"),
                                row.get("status") or "active",
                            ),
                        )
                        customer_map[str(row.get("customer_id"))] = str(cur.fetchone()[0])
                        self._legacy_migration["imported_customers"] = int(self._legacy_migration["imported_customers"]) + 1

                    for row in license_rows:
                        raw_key = str(row.get("license_key") or "").strip()
                        mapped_customer_id = customer_map.get(str(row.get("customer_id")))
                        if not raw_key or not mapped_customer_id:
                            self._legacy_migration["skipped_licenses"] = int(self._legacy_migration["skipped_licenses"]) + 1
                            continue
                        cur.execute(
                            """
                            INSERT INTO licenses(customer_id, license_key_hash, license_key_preview, license_key_prefix, plan_code, status, issued_at, expires_at, revoked_at, notes)
                            VALUES (%s::uuid, %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz, %s::timestamptz, %s)
                            ON CONFLICT (license_key_hash) DO NOTHING
                            """,
                            (
                                mapped_customer_id,
                                hash_secret(raw_key),
                                key_preview(raw_key),
                                LICENSE_PREFIX,
                                row.get("plan_type") or "trial",
                                row.get("status") or "active",
                                row.get("issued_at") or utcnow_iso(),
                                row.get("expires_at"),
                                utcnow_iso() if (row.get("status") or "").lower() == "revoked" else None,
                                row.get("revoked_reason"),
                            ),
                        )
                        if cur.rowcount > 0:
                            self._legacy_migration["imported_licenses"] = int(self._legacy_migration["imported_licenses"]) + 1
                        else:
                            self._legacy_migration["skipped_licenses"] = int(self._legacy_migration["skipped_licenses"]) + 1

    def diagnostic(self) -> dict[str, str]:
        if self._backend == "postgres":
            assert self.database_url is not None
            reachable = "false"
            try:
                with postgres_connection(self.database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        cur.fetchone()
                reachable = "true"
            except Exception:
                reachable = "false"
            return {
                "backend": "postgres",
                "database_url": "configured",
                "postgres_reachable": reachable,
                "legacy_migration_attempted": str(bool(self._legacy_migration["attempted"])).lower(),
                "legacy_migration_imported_customers": str(self._legacy_migration["imported_customers"]),
                "legacy_migration_imported_licenses": str(self._legacy_migration["imported_licenses"]),
                "legacy_migration_skipped_licenses": str(self._legacy_migration["skipped_licenses"]),
            }
        return {"backend": "local_sqlite", "path": str(self.sqlite_path)}

    def list_customers(self) -> list[Customer]:
        if self._backend == "postgres":
            assert self.database_url is not None
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, company_name, COALESCE(contact_name,''), COALESCE(contact_email,''), created_at, COALESCE(notes,'') FROM customers ORDER BY created_at DESC"
                    )
                    rows = cur.fetchall()
            return [
                Customer.from_dict(
                    {
                        "customer_id": str(r[0]),
                        "company_name": r[1],
                        "contact_name": r[2],
                        "contact_email": r[3],
                        "created_at": str(r[4]),
                        "notes": r[5],
                    }
                )
                for r in rows
            ]

        with self._sqlite_connect() as conn:
            rows = conn.execute("SELECT customer_id, company_name, contact_name, contact_email, created_at, notes FROM customers ORDER BY created_at DESC").fetchall()
        return [Customer.from_dict(dict(row)) for row in rows]

    def create_customer(self, company_name: str, contact_name: str, contact_email: str, notes: str = "") -> Customer:
        with self._lock:
            if self._backend == "postgres":
                assert self.database_url is not None
                with postgres_connection(self.database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO customers(company_name, contact_name, contact_email, notes, status)
                            VALUES (%s, %s, %s, %s, 'active')
                            RETURNING id, created_at
                            """,
                            (company_name.strip(), contact_name.strip() or None, contact_email.strip() or None, notes.strip() or None),
                        )
                        row = cur.fetchone()
                customer = Customer(
                    customer_id=str(row[0]),
                    company_name=company_name.strip(),
                    contact_name=contact_name.strip(),
                    contact_email=contact_email.strip(),
                    created_at=str(row[1]),
                    notes=notes.strip(),
                )
                append_audit_event(
                    self.database_url,
                    event_type="customer_created",
                    actor_type="admin_user",
                    actor_identifier=None,
                    target_type="customer",
                    target_id=customer.customer_id,
                    event_data={"company_name": customer.company_name},
                )
                return customer

            customer = Customer(
                customer_id=f"cust_{uuid4().hex[:12]}",
                company_name=company_name.strip(),
                contact_name=contact_name.strip(),
                contact_email=contact_email.strip(),
                created_at=utcnow_iso(),
                notes=notes.strip(),
            )
            with self._sqlite_connect() as conn:
                conn.execute(
                    "INSERT INTO customers(customer_id, company_name, contact_name, contact_email, created_at, notes, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (customer.customer_id, customer.company_name, customer.contact_name, customer.contact_email, customer.created_at, customer.notes, "active"),
                )
                conn.commit()
            return customer

    def get_customer(self, customer_id: str) -> Customer | None:
        safe_id = customer_id.strip()
        if self._backend == "postgres":
            assert self.database_url is not None
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, company_name, COALESCE(contact_name,''), COALESCE(contact_email,''), created_at, COALESCE(notes,'') FROM customers WHERE id = %s::uuid",
                        (safe_id,),
                    )
                    row = cur.fetchone()
            if not row:
                return None
            return Customer.from_dict({"customer_id": str(row[0]), "company_name": row[1], "contact_name": row[2], "contact_email": row[3], "created_at": str(row[4]), "notes": row[5]})

        with self._sqlite_connect() as conn:
            row = conn.execute(
                "SELECT customer_id, company_name, contact_name, contact_email, created_at, notes FROM customers WHERE customer_id = ?",
                (safe_id,),
            ).fetchone()
        return Customer.from_dict(dict(row)) if row else None

    def _license_key_exists(self, key: str) -> bool:
        return self.find_license_by_key(key) is not None

    def generate_license_key(self, plan_type: str) -> str:
        if plan_type.strip().lower() not in ALLOWED_PLAN_TYPES:
            raise ValueError(f"Unsupported plan_type: {plan_type}")
        return generate_prefixed_secret(LICENSE_PREFIX, token_bytes=24)

    def _license_from_pg_row(self, row: Any, *, include_raw_key: str | None = None) -> License:
        return License.from_dict(
            {
                "id": str(row[0]),
                "license_key": include_raw_key or maybe_masked_key(str(row[3]), str(row[2])),
                "customer_id": str(row[1]),
                "plan_type": row[4],
                "status": row[5],
                "issued_at": str(row[6]),
                "expires_at": str(row[7]) if row[7] else None,
                "last_validated_at": None,
                "reset_count": 0,
                "revoked_reason": row[8],
            }
        )

    def list_licenses(self) -> list[License]:
        if self._backend == "postgres":
            assert self.database_url is not None
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, customer_id, license_key_preview, license_key_prefix, plan_code, status, issued_at, expires_at, notes FROM licenses ORDER BY created_at DESC"
                    )
                    rows = cur.fetchall()
            return [self._license_from_pg_row(r) for r in rows]

        with self._sqlite_connect() as conn:
            rows = conn.execute(
                "SELECT license_key, customer_id, plan_type, status, issued_at, expires_at, last_validated_at, reset_count, revoked_reason FROM licenses ORDER BY issued_at DESC"
            ).fetchall()
        return [License.from_dict(dict(row)) for row in rows]

    def find_license_by_key(self, license_key: str) -> License | None:
        safe_key = license_key.strip()
        if not safe_key:
            return None
        if self._backend == "postgres":
            assert self.database_url is not None
            key_hash = hash_secret(safe_key)
            with postgres_connection(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, customer_id, license_key_preview, license_key_prefix, plan_code, status, issued_at, expires_at, notes
                        FROM licenses
                        WHERE license_key_hash = %s OR id::text = %s
                        """,
                        (key_hash, safe_key),
                    )
                    row = cur.fetchone()
            if not row:
                return None
            include_raw = safe_key if safe_key.startswith(f"{LICENSE_PREFIX}-") else None
            return self._license_from_pg_row(row, include_raw_key=include_raw)

        with self._sqlite_connect() as conn:
            row = conn.execute(
                "SELECT license_key, customer_id, plan_type, status, issued_at, expires_at, last_validated_at, reset_count, revoked_reason FROM licenses WHERE license_key = ?",
                (safe_key,),
            ).fetchone()
        return License.from_dict(dict(row)) if row else None

    def create_license(self, customer_id: str, plan_type: str, expires_at: str | None = None) -> License:
        safe_plan = plan_type.strip().lower()
        if safe_plan not in ALLOWED_PLAN_TYPES:
            raise ValueError(f"Unsupported plan_type: {plan_type}")
        if not self.get_customer(customer_id):
            raise ValueError(f"Unknown customer_id: {customer_id}")

        with self._lock:
            key = self.generate_license_key(safe_plan)
            while self._license_key_exists(key):
                key = self.generate_license_key(safe_plan)
            issued_at = utcnow_iso()

            if self._backend == "postgres":
                assert self.database_url is not None
                with postgres_connection(self.database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO licenses(customer_id, license_key_hash, license_key_preview, license_key_prefix, plan_code, features, status, issued_at, expires_at)
                            VALUES (%s::uuid, %s, %s, %s, %s, %s::jsonb, 'active', %s::timestamptz, %s::timestamptz)
                            RETURNING id, customer_id, license_key_preview, license_key_prefix, plan_code, status, issued_at, expires_at, notes
                            """,
                            (
                                customer_id,
                                hash_secret(key),
                                key_preview(key),
                                LICENSE_PREFIX,
                                safe_plan,
                                json.dumps(PLAN_FEATURES.get(safe_plan, {})),
                                issued_at,
                                expires_at,
                            ),
                        )
                        row = cur.fetchone()
                license_obj = self._license_from_pg_row(row, include_raw_key=key)
                append_audit_event(
                    self.database_url,
                    event_type="license_created",
                    actor_type="admin_user",
                    actor_identifier=None,
                    target_type="license",
                    target_id=str(row[0]),
                    event_data={"customer_id": customer_id, "plan_code": safe_plan},
                )
                return license_obj

            license_obj = License(
                license_key=key,
                customer_id=customer_id,
                plan_type=safe_plan,
                status="active",
                issued_at=issued_at,
                expires_at=expires_at,
                last_validated_at=None,
                reset_count=0,
                revoked_reason=None,
            )
            with self._sqlite_connect() as conn:
                conn.execute(
                    "INSERT INTO licenses(license_key, customer_id, plan_type, status, issued_at, expires_at, last_validated_at, reset_count, revoked_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        license_obj.license_key,
                        license_obj.customer_id,
                        license_obj.plan_type,
                        license_obj.status,
                        license_obj.issued_at,
                        license_obj.expires_at,
                        license_obj.last_validated_at,
                        license_obj.reset_count,
                        license_obj.revoked_reason,
                    ),
                )
                conn.commit()
            return license_obj

    def revoke_license(self, license_key: str, reason: str | None = None) -> License:
        safe_key = license_key.strip()
        target = self.find_license_by_key(safe_key)
        if not target:
            raise ValueError("License not found")

        with self._lock:
            if self._backend == "postgres":
                assert self.database_url is not None
                with postgres_connection(self.database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE licenses SET status='revoked', revoked_at=now(), notes=COALESCE(%s, notes) WHERE id=%s::uuid",
                            (reason.strip() if reason else None, target.id),
                        )
                target.status = "revoked"
                target.revoked_reason = reason.strip() if reason else None
                append_audit_event(
                    self.database_url,
                    event_type="license_revoked",
                    actor_type="admin_user",
                    actor_identifier=None,
                    target_type="license",
                    target_id=target.id,
                    event_data={"reason": target.revoked_reason},
                )
                return target

            target.status = "revoked"
            target.revoked_reason = reason.strip() if reason else None
            with self._sqlite_connect() as conn:
                conn.execute("UPDATE licenses SET status=?, revoked_reason=? WHERE license_key=?", (target.status, target.revoked_reason, safe_key))
                conn.commit()
            return target

    def reset_license(self, license_key: str, reason: str | None = None) -> dict[str, License]:
        old = self.revoke_license(license_key, reason=reason or "reset")
        new_license = self.create_license(old.customer_id, old.plan_type, old.expires_at)
        new_license.reset_count = int(old.reset_count or 0) + 1
        return {"old": old, "new": new_license}

    def validate_license(self, license_key: str) -> dict[str, Any]:
        safe_key = license_key.strip()
        if not safe_key:
            return {"valid": False, "reason": "not_found"}

        if self._backend == "postgres":
            assert self.database_url is not None
            key_hash = hash_secret(safe_key)
            with self._lock:
                with postgres_connection(self.database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT l.id, l.customer_id, l.plan_code, l.status, l.expires_at, l.license_key_preview, l.license_key_prefix,
                                   c.company_name
                            FROM licenses l
                            JOIN customers c ON c.id = l.customer_id
                            WHERE l.license_key_hash = %s
                            """,
                            (key_hash,),
                        )
                        row = cur.fetchone()
                        if not row:
                            return {"valid": False, "reason": "not_found"}

                        status = str(row[3]).lower()
                        expires_at = row[4]
                        if status == "revoked":
                            return {"valid": False, "reason": "revoked"}
                        if status == "disabled":
                            return {"valid": False, "reason": "disabled"}
                        if expires_at and expires_at <= datetime.now(timezone.utc):
                            cur.execute("UPDATE licenses SET status='expired' WHERE id=%s::uuid", (str(row[0]),))
                            append_audit_event(
                                self.database_url,
                                event_type="license_expired",
                                actor_type="system",
                                actor_identifier=None,
                                target_type="license",
                                target_id=str(row[0]),
                                event_data={"reason": "expires_at_reached"},
                            )
                            return {"valid": False, "reason": "expired"}
                        if status == "expired":
                            return {"valid": False, "reason": "expired"}

                        return {
                            "valid": True,
                            "customer_id": str(row[1]),
                            "company_name": row[7],
                            "plan_type": row[2],
                            "status": "active",
                            "expires_at": str(expires_at) if expires_at else None,
                            "features": PLAN_FEATURES.get(str(row[2]), {}),
                            "diagnostic": self.diagnostic(),
                        }

        target = self.find_license_by_key(safe_key)
        if not target:
            return {"valid": False, "reason": "not_found"}
        status = str(target.status or "").lower()
        if status == "revoked":
            return {"valid": False, "reason": "revoked"}
        if status == "suspended":
            return {"valid": False, "reason": "suspended"}
        if target.expires_at:
            try:
                expiry = datetime.fromisoformat(str(target.expires_at).replace("Z", "+00:00"))
            except ValueError:
                return {"valid": False, "reason": "invalid_expiration_format"}
            if expiry <= datetime.now(timezone.utc):
                target.status = "expired"
                with self._sqlite_connect() as conn:
                    conn.execute("UPDATE licenses SET status=? WHERE license_key=?", ("expired", safe_key))
                    conn.commit()
                return {"valid": False, "reason": "expired"}
        if status != "active":
            return {"valid": False, "reason": status or "not_found"}
        target.last_validated_at = utcnow_iso()
        with self._sqlite_connect() as conn:
            conn.execute("UPDATE licenses SET last_validated_at=? WHERE license_key=?", (target.last_validated_at, safe_key))
            conn.commit()
        customer = self.get_customer(target.customer_id)
        return {
            "valid": True,
            "customer_id": target.customer_id,
            "company_name": customer.company_name if customer else "Unknown",
            "plan_type": target.plan_type,
            "status": "active",
            "expires_at": target.expires_at,
            "features": PLAN_FEATURES.get(target.plan_type, {}),
            "diagnostic": self.diagnostic(),
        }
