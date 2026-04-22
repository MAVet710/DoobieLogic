# DoobieLogic Licensing System

DoobieLogic is the **license authority**. Buyer Dashboard validates licenses against DoobieLogic; it is never the source of truth.

## Data models

### Customer
- `customer_id`
- `company_name`
- `contact_name`
- `contact_email`
- `created_at`
- `notes`

### License
- `license_key` (opaque, server-generated)
- `customer_id`
- `plan_type` (`trial`, `standard`, `premium`, `enterprise`)
- `status` (`active`, `revoked`, `expired`, `suspended`)
- `issued_at`
- `expires_at` (optional)
- `last_validated_at` (optional)
- `reset_count`
- `revoked_reason` (optional)

## Storage

- FastAPI remains the source of truth for license + key persistence.
- **Production/shared persistence** is configured via `DOOBIE_DATABASE_URL` (or `DATABASE_URL` / `POSTGRES_URL`) and should point to managed Postgres.
- In managed-DB mode, customers, licenses, and API keys are stored in shared SQL tables so Streamlit and FastAPI instances read/write the same durable records.
- Legacy local storage paths still exist for development fallback and migration:
  - `DOOBIE_LICENSE_STORE` (legacy JSON source path; also used to choose local sqlite fallback file location)
  - `DOOBIE_KEY_DB` (legacy local sqlite key DB)
- On first startup with empty SQL tables, `LicenseStore` imports legacy `DOOBIE_LICENSE_STORE` JSON data automatically (non-destructive).
- For split deployments, configure Streamlit admin with:
  - `DOOBIE_ADMIN_API_BASE_URL` (FastAPI base URL)
  - `ADMIN_API_KEY` (bearer token)
  - This routes admin create/list/revoke/reset operations through FastAPI endpoints to avoid storage drift.

## Opaque keys

Keys are generated server-side only, with random segments and plan prefix:
- `DB-PREM-7K4X-9L2Q-AB8T`
- `DB-TRIAL-X8J2-MN4P-Q7ZR`

## Plan features

`PLAN_FEATURES` is centralized in `doobielogic/license_store.py` and returned in successful validation responses.

## Endpoints

### Validation
- `POST /api/v1/license/validate`
- Request: `{ "license_key": "..." }`
- Valid response includes customer, plan, status, expiry, and features.
- Invalid response: `{ "valid": false, "reason": "revoked|expired|not_found|suspended" }`

### Admin
- `POST /api/v1/admin/customers`
- `GET /api/v1/admin/customers`
- `POST /api/v1/admin/licenses/generate`
- `GET /api/v1/admin/licenses`
- `POST /api/v1/admin/licenses/revoke`
- `POST /api/v1/admin/licenses/reset`
- `POST /api/v1/admin/licenses/validate`
- `POST /api/v1/admin/api-keys/generate`
- `GET /api/v1/admin/api-keys`
- `POST /api/v1/admin/api-keys/update`
- `POST /api/v1/admin/api-keys/status`
- `POST /api/v1/admin/api-keys/revoke`

## Auth

- Admin endpoints require `Authorization: Bearer <ADMIN_API_KEY>`.
- Admin endpoints also accept `Authorization: Basic <base64(username:password)>` using the configured admin bcrypt credentials (`DOOBIE_ADMIN_USERNAME` + `DOOBIE_ADMIN_PASSWORD_HASH`) for compatibility.
- Validation endpoint requires the standard Doobie service API key (`DOOBIE_API_KEY`) and accepts either:
  - `x-api-key: <DOOBIE_API_KEY>`
  - `Authorization: Bearer <DOOBIE_API_KEY>`

### Validation request examples

`x-api-key` style:

```bash
curl -X POST http://localhost:8000/api/v1/license/validate \
  -H "x-api-key: $DOOBIE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"license_key":"DB-PREM-7K4X-9L2Q-AB8T"}'
```

`Authorization: Bearer` style:

```bash
curl -X POST http://localhost:8000/api/v1/license/validate \
  -H "Authorization: Bearer $DOOBIE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"license_key":"DB-PREM-7K4X-9L2Q-AB8T"}'
```

### Error behavior

- Invalid or missing service auth returns HTTP `401` with a clear auth error detail.
- Invalid service keys include reason detail (for example not found/revoked/expired) and surface storage mismatch hints.
- Invalid/revoked/expired customer licenses still return normal validation payloads such as:
  - `{"valid": false, "reason": "not_found"}`
  - `{"valid": false, "reason": "revoked"}`

## Deployment contract (Buyer Dashboard integration)

- Deploy FastAPI from `doobielogic.api_v4:app`.
- Health check endpoint: `GET /health`.
- Validation endpoint: `POST /api/v1/license/validate`.
- Buyer Dashboard should target the **FastAPI host** (not Streamlit host).

### Required environment variables

- `DOOBIE_API_KEY`: service auth key expected in either:
  - `x-api-key: <DOOBIE_API_KEY>`
  - `Authorization: Bearer <DOOBIE_API_KEY>`
- `DOOBIE_DATABASE_URL` (recommended): managed Postgres URL used as shared source of truth.
- `DATABASE_URL` / `POSTGRES_URL` can be used as compatibility aliases for `DOOBIE_DATABASE_URL`.
- `DOOBIE_LICENSE_STORE` (optional): legacy JSON path for compatibility import + local fallback.
- `DOOBIE_KEY_DB` (optional): legacy local sqlite key DB path for local-only mode.
- `ADMIN_API_KEY` (optional): needed only for admin endpoints.

## Reset/Revoke behavior

- **Revoke** marks status `revoked` and stores optional reason.
- **Reset** revokes old key, issues a new active key, increments `reset_count`, and preserves customer/plan linkage.
