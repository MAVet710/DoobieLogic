# DoobieLogic

DoobieLogic is a standalone Cannabis AI logic service that:

1. Ingests cannabis sales data from an external API.
2. Normalizes all AI input fields into a single schema.
3. Applies a deterministic Cannabis AI decision engine (scoring + recommendations).
4. Ships state regulation links as first-class data for compliance-aware outputs.
5. Exposes buyer-dashboard-ready APIs so your frontend can consume KPI/risk/recommendation payloads directly.

## Features

- **Standalone API** built with FastAPI.
- **Sales data integration client** (`CannabisSalesAPIClient`) with pagination support.
- **AI logic engine** (`CannabisLogicEngine`) that mimics production-like cannabis logic.
- **Dashboard integration endpoints** for sync + latest KPIs + recommendations.
- **State regulation registry** for all US states + DC.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn doobielogic.api:app --reload
```

## Core endpoints

- `GET /health`
- `GET /states`
- `POST /analyze`
- `POST /sales/ingest`

## Buyer dashboard endpoints

- `POST /dashboard/{buyer_id}/sync`  
  Pulls sales rows from the sales API, normalizes into AI input, runs analysis, stores latest output.
- `POST /dashboard/analyze/store`  
  Allows your dashboard/backend to post already-assembled `CannabisInput` and persist analysis.
- `GET /dashboard/{buyer_id}/latest`  
  Returns latest full analysis object.
- `GET /dashboard/{buyer_id}/kpis`  
  Returns dashboard-ready KPI + risk block.
- `GET /dashboard/{buyer_id}/recommendations`  
  Returns recommendation list for UI cards.
- `GET /dashboard/buyers`  
  Lists buyer IDs currently cached in-memory.

## Environment variables

- `DOOBIE_SALES_API_BASE_URL` (default: `https://api.example.com`)
- `DOOBIE_SALES_API_KEY` (optional)
- `DOOBIE_HTTP_TIMEOUT` (seconds, default `20`)

## Example dashboard sync request

```json
{
  "state": "CA",
  "start_date": "2026-01-01",
  "end_date": "2026-01-31"
}
```
