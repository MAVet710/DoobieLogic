# DoobieLogic

DoobieLogic is a chat-first cannabis AI and API layer for buyers, retailers,
cultivators, processors, manufacturers, packaging teams, compliance teams, and
executives. It combines a conversational model with deterministic KPI logic,
module-specific cannabis curricula, CSV intelligence, and official-source
compliance grounding.

## What DoobieLogic includes

- **Streamlit copilot UI** (`streamlit_app.py`) with:
  - ChatGPT-style chat with automatic specialist routing
  - state and territory selector for legally material questions
  - multi-turn conversation history
  - CSV upload + file intelligence
  - in-app users, passwords, custom roles, and permissions
- **Cannabis module curricula** (`doobielogic/module_curriculum.py`) for
  buying, inventory, dispensary operations, cultivation, extraction, kitchen
  manufacturing, packaging, compliance, operations, and executive decisions
- **Optional conversational AI** (`doobielogic/conversational_ai.py`) through
  the OpenAI Responses API, with a deterministic rules-engine fallback
- **Copilot orchestration** (`doobielogic/copilot.py`)
- **Curated source grounding** (`doobielogic/sourcepack.py`)
- **CSV parsing + mapping** (`doobielogic/parser.py`)
- **Buyer brain heuristics** (`doobielogic/buyer_brain.py`)
- **Deterministic KPI analysis engine** (`doobielogic/engine.py`)
- **API endpoints for dashboard integrations** (`doobielogic/api.py`)

## Grounded vs heuristic outputs

DoobieLogic explicitly separates output types:

- **Grounded source context**: comes from curated source pack links and is labeled with:
  - `grounding`
  - `confidence`
  - `sources`
- **Heuristic file intelligence / buyer brain**: derived from uploaded CSV fields and clearly described as heuristic when rule-based or proxy-based (for example open-to-buy proxy logic).

## CSV upload intelligence

When you upload a CSV in the Streamlit app, DoobieLogic:

1. Parses file bytes into a dataframe.
2. Maps likely cannabis columns (`product`, `category`, `brand`, `price`, `quantity`, `revenue`, `inventory`).
3. Generates structured file insights (price, velocity, revenue, category/brand mix).
4. Runs buyer-brain heuristics:
   - low-velocity detection
   - markdown candidate flags
   - brand/category concentration
   - inventory pressure and open-to-buy style proxy observations
5. Injects these insights into copilot answers when data is available.

## Sample CSV

A realistic demo file is included at:

- `data/sample_inventory.csv`

Use it to test upload flow, quick actions, and buyer-brain signals.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
streamlit run streamlit_app.py
```

The standalone copilot is open by default for local development. For a shared
deployment, set `DOOBIE_REQUIRE_LOGIN=true` and a one-time
`DOOBIE_BOOTSTRAP_TOKEN`. The first-run screen creates the owner account. After
that, administrators create users, reset passwords, activate/deactivate
accounts, and define roles inside the app. Passwords are bcrypt hashes.

For natural multi-turn model answers on Groq's free developer tier, configure:

- `DOOBIE_AI_PROVIDER=groq`
- `GROQ_API_KEY=<secret>`
- `DOOBIE_GROQ_MODEL=openai/gpt-oss-120b`

Without a model key, DoobieLogic remains operational using deterministic
analytics, actionable playbooks, and source grounding. It reports the fallback
in answer details instead of pretending a model answered. OpenAI remains an
optional paid alternative through `DOOBIE_AI_PROVIDER=openai`.

## API run

```bash
uvicorn doobielogic.api_v4:app --host 0.0.0.0 --port 8000
```

## Buyer Dashboard support API contract

DoobieLogic acts as a **support service** for Buyer Dashboard. Buyer Dashboard remains the source of truth for parsing, KPI computation, workflows, and UI.

### Auth

- Set API key in environment:
  - `DOOBIE_API_KEY=your_key_here`
- Send auth header on protected endpoints:
  - `Authorization: Bearer <DOOBIE_API_KEY>` (Buyer Dashboard compatible)
  - or `x-api-key: <DOOBIE_API_KEY>`
- `/health` is public; support and operational endpoints are protected.

### New support endpoints

- `GET /api/v1/auth/check`
- `GET /api/v1/knowledge/modules`
- `GET /api/v1/compliance/jurisdictions`
- `POST /api/v1/support/buyer_brief`
- `POST /api/v1/support/inventory_check`
- `POST /api/v1/support/extraction_brief`
- `POST /api/v1/support/ops_brief`
- `POST /api/v1/support/copilot`

### Standard support response

All support endpoints return this standardized internal contract:

```json
{
  "answer": "string",
  "explanation": "string",
  "recommendations": ["string"],
  "confidence": "high|medium|low",
  "sources": ["string"],
  "mode": "buyer|inventory|extraction|ops|copilot|compliance|executive",
  "risk_flags": ["string"],
  "inefficiencies": ["string"],
  "routed_mode": "string",
  "routed_by": "string",
  "ai": {
    "provider": "openai|rules",
    "model": "string|null",
    "enabled": true,
    "fallback_reason": "string|null"
  }
}
```

### Response modes

DoobieLogic applies a mode-specific response style through `doobielogic/response_system.py`:

- **buyer**: assortment gaps, dead inventory, velocity, reorder pressure, margin-aware actions.
- **inventory**: low stock, overstock, DOH imbalance, immediate tactical actions.
- **extraction**: yield, stage loss, failed batches, throughput, formulation/terpene context, cost/value/margin.
- **ops**: bottlenecks, recurring risk, ownership, execution.
- **copilot**: direct answer first, explanation second, practical next step.
- **compliance**: conservative framing, traceability, recurrence, verification.
- **executive**: concise summary, cross-functional issues, decision-ready next actions.

Confidence is inferred from structured data coverage, source grounding, and relevant operational/compliance rulesâ€”not hardcoded.

### Compliance coverage and evidence policy

Compliance coverage includes all 50 states, the District of Columbia, American
Samoa, Guam, the Northern Mariana Islands, Puerto Rico, and the U.S. Virgin
Islands. The registry exposes official authority and law/rule entry points,
program scope, source-review date, confidence, and review status.

Registry links are not treated as exact current rule text. When an exact rule is
not present in the curated corpus, DoobieLogic states the limitation, provides
the official authority link, and requires regulator or qualified-counsel
verification before action.

### Example request

```bash
curl -X POST http://localhost:8000/api/v1/support/buyer_brief \
  -H "Authorization: Bearer $DOOBIE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question":"What inventory needs attention?","state":"CA","data":{"days_on_hand":10}}'
```

## Tests

```bash
python -m pytest -q
```


## Licensing and admin

DoobieLogic now includes an opaque server-side licensing system used by Buyer Dashboard validation.

- License authority is DoobieLogic (server-side key status is source of truth).
- Admin management endpoints are protected with `Authorization: Bearer <ADMIN_API_KEY>`.
- License validation endpoint is `POST /api/v1/license/validate` (service key protected).
- A lightweight internal admin panel is available via `streamlit_admin.py`.
- For split deployments (Streamlit Cloud + Render), configure Streamlit admin to use FastAPI as the source of truth:
  - `DOOBIE_ADMIN_API_BASE_URL=https://<your-fastapi-host>`
  - `ADMIN_API_KEY=<admin bearer token>`
  - This makes Streamlit key/license operations call FastAPI admin endpoints instead of writing local files.

Validation request supports either service-auth header style:

```bash
curl -X POST http://localhost:8000/api/v1/license/validate \
  -H "x-api-key: $DOOBIE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"license_key":"DB-PREM-7K4X-9L2Q-AB8T"}'
```

```bash
curl -X POST http://localhost:8000/api/v1/license/validate \
  -H "Authorization: Bearer $DOOBIE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"license_key":"DB-PREM-7K4X-9L2Q-AB8T"}'
```

See full documentation in `docs/licensing.md`.

## Deployment requirements for Buyer Dashboard license validation

- Deploy the **FastAPI app** from `doobielogic.api_v4:app` (not Streamlit).
- Buyer Dashboard license checks must call the FastAPI host:
  - `POST <FASTAPI_BASE_URL>/api/v1/license/validate`
- Required environment variables on the FastAPI service:
  - `DOOBIE_API_KEY` (service authentication key)
  - `DATABASE_URL` (or `DOOBIE_DATABASE_URL` / `POSTGRES_URL`) for persistent shared Postgres storage
  - `DOOBIE_BACKEND_MODE=postgres` (recommended for production clarity; local mode is dev-only)
  - `DOOBIE_STRICT_CONFIG=true`
  - `DOOBIE_AI_PROVIDER=groq`, `GROQ_API_KEY`, and `DOOBIE_GROQ_MODEL=openai/gpt-oss-120b` for free-tier conversational answers
- Optional admin key:
  - `ADMIN_API_KEY` (for admin endpoints only)
- Health probe:
  - `GET <FASTAPI_BASE_URL>/health`


For full production persistence setup, see `docs/postgres_persistence.md`.
