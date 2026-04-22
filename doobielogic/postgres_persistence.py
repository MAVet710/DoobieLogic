from __future__ import annotations

import hashlib
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator
from urllib.parse import urlparse

try:
    import psycopg
except Exception:  # pragma: no cover
    psycopg = None


def is_postgres_url(database_url: str | None) -> bool:
    if not database_url:
        return False
    return urlparse(database_url).scheme.lower() in {"postgres", "postgresql"}


def hash_secret(raw_value: str) -> str:
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def key_preview(raw_value: str, *, suffix_length: int = 8) -> str:
    safe = (raw_value or "").strip()
    if not safe:
        return ""
    if len(safe) <= suffix_length:
        return safe
    return safe[-suffix_length:]


def generate_prefixed_secret(prefix: str, *, token_bytes: int = 24) -> str:
    return f"{prefix}-{secrets.token_urlsafe(token_bytes)}"


def maybe_masked_key(prefix: str, preview: str) -> str:
    return f"{prefix}-****{preview}"


@contextmanager
def postgres_connection(database_url: str) -> Iterator[Any]:
    if psycopg is None:
        raise RuntimeError("Postgres database URL configured but psycopg is not installed.")
    conn = psycopg.connect(database_url)
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_postgres_schema(database_url: str) -> None:
    ddl = [
        "CREATE EXTENSION IF NOT EXISTS pgcrypto",
        """
        CREATE TABLE IF NOT EXISTS customers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_name TEXT NOT NULL,
            contact_name TEXT,
            contact_email TEXT,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS licenses (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            license_key_hash TEXT NOT NULL UNIQUE,
            license_key_preview TEXT NOT NULL,
            license_key_prefix TEXT NOT NULL DEFAULT 'DLB-LIC',
            plan_code TEXT NOT NULL,
            features JSONB NOT NULL DEFAULT '{}'::jsonb,
            status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked', 'expired', 'disabled')),
            issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ,
            revoked_at TIMESTAMPTZ,
            created_by TEXT,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            key_type TEXT NOT NULL CHECK (key_type IN ('admin', 'service')),
            key_hash TEXT NOT NULL UNIQUE,
            key_preview TEXT NOT NULL,
            key_prefix TEXT NOT NULL,
            label TEXT NOT NULL,
            scope TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked', 'expired', 'disabled')),
            created_by TEXT,
            notes TEXT,
            issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ,
            revoked_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type TEXT NOT NULL,
            actor_type TEXT NOT NULL CHECK (actor_type IN ('admin_user', 'admin_api_key', 'service_api_key', 'system')),
            actor_identifier TEXT,
            target_type TEXT,
            target_id UUID,
            event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE OR REPLACE FUNCTION set_updated_at_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """,
        "DROP TRIGGER IF EXISTS trg_customers_updated_at ON customers",
        "CREATE TRIGGER trg_customers_updated_at BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION set_updated_at_timestamp()",
        "DROP TRIGGER IF EXISTS trg_licenses_updated_at ON licenses",
        "CREATE TRIGGER trg_licenses_updated_at BEFORE UPDATE ON licenses FOR EACH ROW EXECUTE FUNCTION set_updated_at_timestamp()",
        "DROP TRIGGER IF EXISTS trg_api_keys_updated_at ON api_keys",
        "CREATE TRIGGER trg_api_keys_updated_at BEFORE UPDATE ON api_keys FOR EACH ROW EXECUTE FUNCTION set_updated_at_timestamp()",
        "CREATE INDEX IF NOT EXISTS idx_customers_company_name ON customers(company_name)",
        "CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status)",
        "CREATE INDEX IF NOT EXISTS idx_licenses_customer_id ON licenses(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status)",
        "CREATE INDEX IF NOT EXISTS idx_licenses_created_at ON licenses(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_api_keys_key_type ON api_keys(key_type)",
        "CREATE INDEX IF NOT EXISTS idx_api_keys_scope ON api_keys(scope)",
        "CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status)",
        "CREATE INDEX IF NOT EXISTS idx_api_keys_created_at ON api_keys(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_audit_events_created_at ON audit_events(created_at DESC)",
    ]

    with postgres_connection(database_url) as conn:
        with conn.cursor() as cur:
            for statement in ddl:
                cur.execute(statement)


def append_audit_event(
    database_url: str,
    *,
    event_type: str,
    actor_type: str,
    actor_identifier: str | None,
    target_type: str | None,
    target_id: str | None,
    event_data: dict[str, Any] | None = None,
) -> None:
    with postgres_connection(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_events(event_type, actor_type, actor_identifier, target_type, target_id, event_data)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    event_type,
                    actor_type,
                    actor_identifier,
                    target_type,
                    target_id,
                    __import__("json").dumps(event_data or {}),
                ),
            )
