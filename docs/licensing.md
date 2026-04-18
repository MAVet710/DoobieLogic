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

- Backed by local JSON storage (`data/license_store.json` by default).
- Configurable via `DOOBIE_LICENSE_STORE` environment variable.

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

## Auth

- Admin endpoints require `Authorization: Bearer <ADMIN_API_KEY>`.
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
- `DOOBIE_LICENSE_STORE` (optional): path to JSON license store (defaults to `data/license_store.json`).
- `DOOBIE_KEY_DB` (optional): path to service API key sqlite DB (defaults to `data/key_store.db`).
- `ADMIN_API_KEY` (optional): needed only for admin endpoints.

## Reset/Revoke behavior

- **Revoke** marks status `revoked` and stores optional reason.
- **Reset** revokes old key, issues a new active key, increments `reset_count`, and preserves customer/plan linkage.
