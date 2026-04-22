from __future__ import annotations

import json
import secrets
import sqlite3
import string
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

try:
    import psycopg
except Exception:  # pragma: no cover
    psycopg = None

from doobielogic.license_models import ALLOWED_PLAN_TYPES, Customer, License

PLAN_FEATURES: dict[str, dict[str, bool]] = {
    "trial": {"buyer_module": True, "extraction_module": False, "ai_support": True, "admin_exports": False},
    "standard": {"buyer_module": True, "extraction_module": True, "ai_support": True, "admin_exports": False},
    "premium": {"buyer_module": True, "extraction_module": True, "ai_support": True, "admin_exports": True},
    "enterprise": {"buyer_module": True, "extraction_module": True, "ai_support": True, "admin_exports": True},
}

_PLAN_PREFIX = {"trial": "TRIAL", "standard": "STD", "premium": "PREM", "enterprise": "ENT"}


def _is_postgres_url(database_url: str | None) -> bool:
    if not database_url:
        return False
    scheme = urlparse(database_url).scheme.lower()
    return scheme in {"postgres", "postgresql"}


class LicenseStore:
    def __init__(self, path: str | Path = "data/license_store.json", *, database_url: str | None = None):
        self.path = Path(path)
        self.database_url = (database_url or "").strip() or None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.sqlite_path = self.path.with_suffix(".db")
        self._lock = Lock()
        self._backend = "postgres" if _is_postgres_url(self.database_url) else "sqlite"
        if self._backend == "postgres" and psycopg is None:
            raise RuntimeError("Postgres database URL configured but psycopg is not installed.")
        self._init_db()
        self._migrate_legacy_json_if_needed()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _sqlite_connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _postgres_connect(self):
        assert self.database_url is not None
        assert psycopg is not None
        conn = psycopg.connect(self.database_url)
        conn.autocommit = False
        return conn

    def _init_db(self) -> None:
        ddl = [
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                contact_email TEXT NOT NULL,
                created_at TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT ''
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
            "CREATE INDEX IF NOT EXISTS idx_licenses_customer_id ON licenses(customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status)",
        ]

        if self._backend == "postgres":
            with self._postgres_connect() as conn:
                with conn.cursor() as cur:
                    for statement in ddl:
                        cur.execute(statement)
                conn.commit()
            return

        with self._sqlite_connect() as conn:
            for statement in ddl:
                conn.execute(statement)
            conn.commit()

    def _table_count(self, table_name: str) -> int:
        binder = "%s" if self._backend == "postgres" else "?"
        sql = f"SELECT COUNT(1) FROM {table_name}"
        if self._backend == "postgres":
            with self._postgres_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    row = cur.fetchone()
                    return int((row or [0])[0])
        with self._sqlite_connect() as conn:
            row = conn.execute(sql).fetchone()
            return int((row or [0])[0])

    def _migrate_legacy_json_if_needed(self) -> None:
        if not self.path.exists():
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
            if self._backend == "postgres":
                with self._postgres_connect() as conn:
                    with conn.cursor() as cur:
                        for row in customers:
                            cur.execute(
                                """
                                INSERT INTO customers(customer_id, company_name, contact_name, contact_email, created_at, notes)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (customer_id) DO NOTHING
                                """,
                                (
                                    row["customer_id"],
                                    row["company_name"],
                                    row["contact_name"],
                                    row["contact_email"],
                                    row["created_at"],
                                    row.get("notes") or "",
                                ),
                            )
                        for row in licenses:
                            cur.execute(
                                """
                                INSERT INTO licenses(license_key, customer_id, plan_type, status, issued_at, expires_at, last_validated_at, reset_count, revoked_reason)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (license_key) DO NOTHING
                                """,
                                (
                                    row["license_key"],
                                    row["customer_id"],
                                    row["plan_type"],
                                    row["status"],
                                    row["issued_at"],
                                    row.get("expires_at"),
                                    row.get("last_validated_at"),
                                    int(row.get("reset_count") or 0),
                                    row.get("revoked_reason"),
                                ),
                            )
                    conn.commit()
                return

            with self._sqlite_connect() as conn:
                for row in customers:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO customers(customer_id, company_name, contact_name, contact_email, created_at, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (row["customer_id"], row["company_name"], row["contact_name"], row["contact_email"], row["created_at"], row.get("notes") or ""),
                    )
                for row in licenses:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO licenses(license_key, customer_id, plan_type, status, issued_at, expires_at, last_validated_at, reset_count, revoked_reason)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["license_key"],
                            row["customer_id"],
                            row["plan_type"],
                            row["status"],
                            row["issued_at"],
                            row.get("expires_at"),
                            row.get("last_validated_at"),
                            int(row.get("reset_count") or 0),
                            row.get("revoked_reason"),
                        ),
                    )
                conn.commit()

    def diagnostic(self) -> dict[str, str]:
        if self._backend == "postgres":
            return {"backend": "postgres", "database_url": "configured"}
        return {"backend": "local_sqlite", "path": str(self.sqlite_path)}

    def list_customers(self) -> list[Customer]:
        if self._backend == "postgres":
            with self._postgres_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT customer_id, company_name, contact_name, contact_email, created_at, notes FROM customers ORDER BY created_at DESC")
                    rows = cur.fetchall()
            return [Customer.from_dict({"customer_id": r[0], "company_name": r[1], "contact_name": r[2], "contact_email": r[3], "created_at": r[4], "notes": r[5]}) for r in rows]

        with self._sqlite_connect() as conn:
            rows = conn.execute("SELECT customer_id, company_name, contact_name, contact_email, created_at, notes FROM customers ORDER BY created_at DESC").fetchall()
        return [Customer.from_dict(dict(row)) for row in rows]

    def list_licenses(self) -> list[License]:
        if self._backend == "postgres":
            with self._postgres_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT license_key, customer_id, plan_type, status, issued_at, expires_at, last_validated_at, reset_count, revoked_reason FROM licenses ORDER BY issued_at DESC"
                    )
                    rows = cur.fetchall()
            return [License.from_dict({"license_key": r[0], "customer_id": r[1], "plan_type": r[2], "status": r[3], "issued_at": r[4], "expires_at": r[5], "last_validated_at": r[6], "reset_count": r[7], "revoked_reason": r[8]}) for r in rows]

        with self._sqlite_connect() as conn:
            rows = conn.execute(
                "SELECT license_key, customer_id, plan_type, status, issued_at, expires_at, last_validated_at, reset_count, revoked_reason FROM licenses ORDER BY issued_at DESC"
            ).fetchall()
        return [License.from_dict(dict(row)) for row in rows]

    def get_customer(self, customer_id: str) -> Customer | None:
        safe_id = customer_id.strip()
        if self._backend == "postgres":
            with self._postgres_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT customer_id, company_name, contact_name, contact_email, created_at, notes FROM customers WHERE customer_id = %s",
                        (safe_id,),
                    )
                    row = cur.fetchone()
            return Customer.from_dict({"customer_id": row[0], "company_name": row[1], "contact_name": row[2], "contact_email": row[3], "created_at": row[4], "notes": row[5]}) if row else None

        with self._sqlite_connect() as conn:
            row = conn.execute(
                "SELECT customer_id, company_name, contact_name, contact_email, created_at, notes FROM customers WHERE customer_id = ?",
                (safe_id,),
            ).fetchone()
        return Customer.from_dict(dict(row)) if row else None

    def create_customer(self, company_name: str, contact_name: str, contact_email: str, notes: str = "") -> Customer:
        customer = Customer(
            customer_id=f"cust_{uuid4().hex[:12]}",
            company_name=company_name.strip(),
            contact_name=contact_name.strip(),
            contact_email=contact_email.strip(),
            created_at=self._now_iso(),
            notes=notes.strip(),
        )
        with self._lock:
            if self._backend == "postgres":
                with self._postgres_connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO customers(customer_id, company_name, contact_name, contact_email, created_at, notes)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (customer.customer_id, customer.company_name, customer.contact_name, customer.contact_email, customer.created_at, customer.notes),
                        )
                    conn.commit()
            else:
                with self._sqlite_connect() as conn:
                    conn.execute(
                        """
                        INSERT INTO customers(customer_id, company_name, contact_name, contact_email, created_at, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (customer.customer_id, customer.company_name, customer.contact_name, customer.contact_email, customer.created_at, customer.notes),
                    )
                    conn.commit()
        return customer

    def find_license_by_key(self, license_key: str) -> License | None:
        safe_key = license_key.strip()
        if self._backend == "postgres":
            with self._postgres_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT license_key, customer_id, plan_type, status, issued_at, expires_at, last_validated_at, reset_count, revoked_reason FROM licenses WHERE license_key = %s",
                        (safe_key,),
                    )
                    row = cur.fetchone()
            return License.from_dict({"license_key": row[0], "customer_id": row[1], "plan_type": row[2], "status": row[3], "issued_at": row[4], "expires_at": row[5], "last_validated_at": row[6], "reset_count": row[7], "revoked_reason": row[8]}) if row else None

        with self._sqlite_connect() as conn:
            row = conn.execute(
                "SELECT license_key, customer_id, plan_type, status, issued_at, expires_at, last_validated_at, reset_count, revoked_reason FROM licenses WHERE license_key = ?",
                (safe_key,),
            ).fetchone()
        return License.from_dict(dict(row)) if row else None

    def _license_key_exists(self, key: str) -> bool:
        return self.find_license_by_key(key) is not None

    def generate_license_key(self, plan_type: str) -> str:
        safe_plan = plan_type.strip().lower()
        if safe_plan not in ALLOWED_PLAN_TYPES:
            raise ValueError(f"Unsupported plan_type: {plan_type}")
        alphabet = string.ascii_uppercase + string.digits
        prefix = _PLAN_PREFIX[safe_plan]
        return f"DB-{prefix}-{''.join(secrets.choice(alphabet) for _ in range(4))}-{''.join(secrets.choice(alphabet) for _ in range(4))}-{''.join(secrets.choice(alphabet) for _ in range(4))}"

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
            license_obj = License(
                license_key=key,
                customer_id=customer_id,
                plan_type=safe_plan,
                status="active",
                issued_at=self._now_iso(),
                expires_at=expires_at,
                last_validated_at=None,
                reset_count=0,
                revoked_reason=None,
            )
            if self._backend == "postgres":
                with self._postgres_connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO licenses(license_key, customer_id, plan_type, status, issued_at, expires_at, last_validated_at, reset_count, revoked_reason)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
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
            else:
                with self._sqlite_connect() as conn:
                    conn.execute(
                        """
                        INSERT INTO licenses(license_key, customer_id, plan_type, status, issued_at, expires_at, last_validated_at, reset_count, revoked_reason)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
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
        with self._lock:
            target = self.find_license_by_key(safe_key)
            if not target:
                raise ValueError("License not found")
            target.status = "revoked"
            target.revoked_reason = reason.strip() if reason else None
            if self._backend == "postgres":
                with self._postgres_connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE licenses SET status=%s, revoked_reason=%s WHERE license_key=%s", (target.status, target.revoked_reason, safe_key))
                    conn.commit()
            else:
                with self._sqlite_connect() as conn:
                    conn.execute("UPDATE licenses SET status=?, revoked_reason=? WHERE license_key=?", (target.status, target.revoked_reason, safe_key))
                    conn.commit()
            return target

    def reset_license(self, license_key: str, reason: str | None = None) -> dict[str, License]:
        safe_key = license_key.strip()
        with self._lock:
            old = self.find_license_by_key(safe_key)
            if not old:
                raise ValueError("License not found")
            old.status = "revoked"
            old.revoked_reason = reason.strip() if reason else "reset"
            next_reset_count = int(old.reset_count or 0) + 1

            key = self.generate_license_key(old.plan_type)
            while self._license_key_exists(key):
                key = self.generate_license_key(old.plan_type)

            new_license = License(
                license_key=key,
                customer_id=old.customer_id,
                plan_type=old.plan_type,
                status="active",
                issued_at=self._now_iso(),
                expires_at=old.expires_at,
                last_validated_at=None,
                reset_count=next_reset_count,
                revoked_reason=None,
            )

            if self._backend == "postgres":
                with self._postgres_connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE licenses SET status=%s, revoked_reason=%s WHERE license_key=%s",
                            (old.status, old.revoked_reason, old.license_key),
                        )
                        cur.execute(
                            """
                            INSERT INTO licenses(license_key, customer_id, plan_type, status, issued_at, expires_at, last_validated_at, reset_count, revoked_reason)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                new_license.license_key,
                                new_license.customer_id,
                                new_license.plan_type,
                                new_license.status,
                                new_license.issued_at,
                                new_license.expires_at,
                                new_license.last_validated_at,
                                new_license.reset_count,
                                new_license.revoked_reason,
                            ),
                        )
                    conn.commit()
            else:
                with self._sqlite_connect() as conn:
                    conn.execute("UPDATE licenses SET status=?, revoked_reason=? WHERE license_key=?", (old.status, old.revoked_reason, old.license_key))
                    conn.execute(
                        """
                        INSERT INTO licenses(license_key, customer_id, plan_type, status, issued_at, expires_at, last_validated_at, reset_count, revoked_reason)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            new_license.license_key,
                            new_license.customer_id,
                            new_license.plan_type,
                            new_license.status,
                            new_license.issued_at,
                            new_license.expires_at,
                            new_license.last_validated_at,
                            new_license.reset_count,
                            new_license.revoked_reason,
                        ),
                    )
                    conn.commit()

        return {"old": old, "new": new_license}

    def validate_license(self, license_key: str) -> dict[str, Any]:
        safe_key = license_key.strip()
        with self._lock:
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
                    if self._backend == "postgres":
                        with self._postgres_connect() as conn:
                            with conn.cursor() as cur:
                                cur.execute("UPDATE licenses SET status=%s WHERE license_key=%s", ("expired", safe_key))
                            conn.commit()
                    else:
                        with self._sqlite_connect() as conn:
                            conn.execute("UPDATE licenses SET status=? WHERE license_key=?", ("expired", safe_key))
                            conn.commit()
                    return {"valid": False, "reason": "expired"}

            if status != "active":
                return {"valid": False, "reason": status or "not_found"}

            target.last_validated_at = self._now_iso()
            if self._backend == "postgres":
                with self._postgres_connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE licenses SET last_validated_at=%s WHERE license_key=%s", (target.last_validated_at, safe_key))
                    conn.commit()
            else:
                with self._sqlite_connect() as conn:
                    conn.execute("UPDATE licenses SET last_validated_at=? WHERE license_key=?", (target.last_validated_at, safe_key))
                    conn.commit()

            customer = self.get_customer(target.customer_id)
            company_name = customer.company_name if customer else "Unknown"
            plan_type = target.plan_type

            return {
                "valid": True,
                "customer_id": target.customer_id,
                "company_name": company_name,
                "plan_type": plan_type,
                "status": "active",
                "expires_at": target.expires_at,
                "features": PLAN_FEATURES.get(plan_type, {}),
                "diagnostic": self.diagnostic(),
            }
