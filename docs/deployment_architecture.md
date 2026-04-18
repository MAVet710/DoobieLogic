# DoobieLogic Deployment Architecture

This project is intended to run as **separate services**:

1. **Doobie Streamlit Admin UI** (internal/admin operations)
2. **Doobie FastAPI API v4** (Buyer Dashboard integration + license validation)
3. **Buyer Dashboard Streamlit app** (external consumer of Doobie FastAPI)

---

## 1) Doobie Streamlit Admin UI

### Purpose
- Admin/customer setup
- License generation and lifecycle actions
- Service API key management

### Entrypoints
- `streamlit_admin.py`
- `pages/1_Key_Management.py`

### Required settings
- `DOOBIE_LICENSE_STORE` (shared license store path)
- `DOOBIE_KEY_DB` (shared API key DB path)
- Admin auth settings (see `doobielogic/admin_auth.py`)

---

## 2) Doobie FastAPI API

### Purpose
- Public integration surface for Buyer Dashboard
- License validation endpoint
- Support/copilot API endpoints

### Entrypoint
- `doobielogic.api_v4:app`

### Render start command
```bash
uvicorn doobielogic.api_v4:app --host 0.0.0.0 --port $PORT
```

### Required environment variables
- `DOOBIE_API_KEY` (service auth key expected from Buyer Dashboard)
- `DOOBIE_LICENSE_STORE` (shared license store path)
- `DOOBIE_KEY_DB` (shared API key DB path if generated scoped API keys are used)

### Optional environment variables
- `ADMIN_API_KEY` (admin API endpoints)
- `DOOBIE_KEY_VALIDATION_TOKEN` (`/api/v1/keys/validate` protection)

### Required endpoints
- `GET /health`
- `POST /api/v1/license/validate` with body:
  - `{"license_key":"<customer-license-key>"}`

### Accepted auth headers for service requests
- `x-api-key: <DOOBIE_API_KEY>`
- `Authorization: Bearer <DOOBIE_API_KEY>`

---

## 3) Buyer Dashboard

### Target URL
Buyer Dashboard must point to the **Doobie FastAPI base URL**, not Doobie Streamlit.

### Supported buyer config variables
- `DOOBIE_BASE_URL` or `DOOBIELOGIC_URL` (base API URL)
- `DOOBIE_API_KEY` or `DOOBIELOGIC_API_KEY` (service key)

### License flow
1. Customer receives Doobie-generated license key.
2. Buyer Dashboard calls `POST /api/v1/license/validate`.
3. Doobie API authenticates service request key.
4. API returns either:
   - valid license payload
   - invalid license payload (`not_found`, `revoked`, `expired`, etc.)
   - clear 401 auth error if service key is missing/wrong.

---

## Shared storage contract

`DOOBIE_LICENSE_STORE` and `DOOBIE_KEY_DB` must point to a **shared persistent volume or external storage** reachable by both:
- Doobie Streamlit admin service
- Doobie FastAPI service

If these services are deployed separately with local ephemeral files, key/license drift will occur.
