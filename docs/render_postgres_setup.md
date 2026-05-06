# Render Postgres Setup for Persistent Keys/Licenses

Use this when deploying DoobieLogic on Render so API keys and license records persist across redeploys.

## 1) Open service environment settings

- Render → **DoobieLogic Web Service** → **Environment**.

## 2) Add required variables

```bash
DOOBIE_DATABASE_URL=<Render Postgres Internal Database URL>
DOOBIE_BACKEND_MODE=auto
```

Optional hardening:

```bash
DOOBIE_STRICT_CONFIG=true
```

Notes:
- `DOOBIE_DATABASE_URL` is the preferred DB variable.
- Compatibility fallbacks also supported: `DATABASE_URL`, `POSTGRES_URL`.
- `DOOBIE_BACKEND_MODE` is the preferred backend mode variable.
- Legacy alias `BACKEND_MODE` is accepted, but keep using `DOOBIE_BACKEND_MODE` going forward.

## 3) Redeploy

Redeploy the web service after saving env vars.

## 4) Verify health

Request:

```bash
curl https://<your-service>/health
```

Expected fields in healthy production mode:
- `postgres_configured: true`
- `postgres_reachable: true`
- `database_url_source: DOOBIE_DATABASE_URL` (or fallback variable name)
- `license_store_backend: postgres`
- `key_store_backend: postgres`
- `source_of_truth: postgres_shared`

If health reports local mode in production, warnings include:
- `Keys and licenses are deployment-local and may not survive redeploys.`

## 5) Regenerate cross-deployment credentials after cutover

After moving from local sqlite to Postgres, regenerate as needed:
- Buyer Dashboard service API key
- customer license keys (if old keys were only in deployment-local sqlite)

Reason: old deployment-local keys/licenses may not exist in the shared Postgres store.

## 6) Optional strict production guardrail

With `DOOBIE_STRICT_CONFIG=true`, startup fails in production-like environments if no DB URL is configured.
This prevents accidental deployment-local key/license storage.
