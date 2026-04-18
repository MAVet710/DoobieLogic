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
- Validation endpoint uses the standard Doobie service API key (`DOOBIE_API_KEY`, via `x-api-key`).
  - Buyer Dashboard compatibility: `Authorization: Bearer <DOOBIE_API_KEY>` is also accepted.

## Reset/Revoke behavior

- **Revoke** marks status `revoked` and stores optional reason.
- **Reset** revokes old key, issues a new active key, increments `reset_count`, and preserves customer/plan linkage.
