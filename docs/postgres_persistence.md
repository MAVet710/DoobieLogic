# Postgres persistence (cloud mode)

DoobieLogic now uses a shared Postgres schema as the source of truth for long-lived records when a Postgres URL is configured.

## Required env vars

- Postgres URL (first non-empty wins): `DOOBIE_DATABASE_URL`, then `DATABASE_URL`, then `POSTGRES_URL`.
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

- Local SQLite/JSON persistence remains available only for local fallback mode.
- Existing legacy records are imported into Postgres at startup when Postgres mode is active:
  - `license_store.json`
  - `license_store.db` (derived from legacy JSON path)
  - `key_store.db`
- Legacy files are not deleted.
- Health/diagnostic routes expose active backend and Postgres reachability so operators can confirm cloud mode is actually active.


## Render production setup

Use persistent Postgres-backed storage in production.

Required:
- `DATABASE_URL` (or `DOOBIE_DATABASE_URL` / `POSTGRES_URL`) pointing to your managed Postgres instance.
- `DOOBIE_BACKEND_MODE=postgres` (alias of remote mode for production clarity).
- `ADMIN_API_KEY` (or complete the bootstrap admin key flow after deploy).

Behavior:
- When a Postgres URL is present, `LicenseStore` and `KeyStore` initialize shared Postgres schema and use Postgres as source of truth.
- `/health` reports `postgres_configured`, `postgres_reachable`, `license_store_backend`, `key_store_backend`, and `source_of_truth`.
- If production-like env is detected while local mode is active, health warns: `Keys and licenses are deployment-local and may not survive redeploys.`

Important migration note:
- Local-mode service keys and licenses are deployment-local. After switching to Postgres mode, regenerate active service/admin keys and licenses from the shared store.
