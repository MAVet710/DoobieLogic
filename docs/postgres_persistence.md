# Postgres persistence (cloud mode)

DoobieLogic now uses a shared Postgres schema as the source of truth for long-lived records when `DATABASE_URL` (or `DOOBIE_DATABASE_URL`) is configured.

## Required env vars

- `DATABASE_URL` (or `DOOBIE_DATABASE_URL`): Postgres connection URL.
- `DOOBIE_BACKEND_MODE`: `auto`, `local`, or `remote_api`.
- `DOOBIE_ADMIN_API_BASE_URL` + `ADMIN_API_KEY` for split Streamlit/FastAPI deployments.

## Schema

Schema initialization is automatic on startup of `LicenseStore`/`KeyStore` with Postgres URLs. The following tables are created if missing:

- `customers`
- `licenses`
- `api_keys`
- `audit_events`

`pgcrypto` is enabled for UUID generation (`gen_random_uuid()`), `updated_at` triggers are installed for mutable tables, and indexes are added for common admin query patterns.

## Security model

- Raw admin/service/license keys are generated once.
- Only SHA-256 hash + key preview + metadata are stored.
- Raw keys are returned only at create-time responses.
- Validation hashes incoming keys and compares hash values.

## Legacy compatibility

- Local SQLite/JSON persistence remains available for local fallback mode.
- Existing `license_store.json` and `key_store.db` records are imported into Postgres the first time Postgres-backed startup occurs on an empty schema.
- Legacy files are not deleted.
