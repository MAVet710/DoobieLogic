from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .dashboard import BuyerWorkspaceStore
from .engine import CannabisLogicEngine
from .models import CannabisInput, CannabisOutput
from .normalizer import normalize_sales_rows_to_input
from .regulations import REGULATION_LINKS
from .sales_api import CannabisSalesAPIClient

app = FastAPI(title="DoobieLogic", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = CannabisLogicEngine()
sales_client = CannabisSalesAPIClient()
store = BuyerWorkspaceStore()


class SalesIngestRequest(BaseModel):
    state: str = Field(min_length=2, max_length=2)
    start_date: date
    end_date: date


class DashboardSyncRequest(BaseModel):
    state: str = Field(min_length=2, max_length=2)
    start_date: date
    end_date: date


class DashboardAnalyzeRequest(BaseModel):
    buyer_id: str = Field(min_length=1)
    payload: CannabisInput


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "DoobieLogic"}


@app.get("/states")
def states() -> dict[str, dict[str, str]]:
    return REGULATION_LINKS


@app.post("/analyze", response_model=CannabisOutput)
def analyze(payload: CannabisInput) -> CannabisOutput:
    if payload.state not in REGULATION_LINKS:
        raise HTTPException(status_code=400, detail=f"Unsupported state code: {payload.state}")
    return engine.analyze(payload)


@app.post("/sales/ingest")
def sales_ingest(req: SalesIngestRequest):
    rows = sales_client.fetch_sales(req.state.upper(), str(req.start_date), str(req.end_date))
    return {"state": req.state.upper(), "rows": len(rows), "preview": rows[:3]}


@app.post("/dashboard/{buyer_id}/sync")
def dashboard_sync(buyer_id: str, req: DashboardSyncRequest):
    rows = sales_client.fetch_sales(req.state.upper(), str(req.start_date), str(req.end_date))
    normalized = normalize_sales_rows_to_input(req.state.upper(), req.start_date, req.end_date, rows)
    output = engine.analyze(normalized)

    workspace = store.get_or_create(buyer_id)
    workspace.sales_rows = rows
    workspace.latest_input = normalized
    workspace.latest_output = output
    workspace.last_synced_at = req.end_date

    return {
        "buyer_id": buyer_id,
        "synced_rows": len(rows),
        "score": output.score,
        "tier": output.tier,
        "recommendations": output.recommendations,
    }


@app.post("/dashboard/analyze/store", response_model=CannabisOutput)
def dashboard_analyze_store(req: DashboardAnalyzeRequest) -> CannabisOutput:
    output = analyze(req.payload)
    workspace = store.get_or_create(req.buyer_id)
    workspace.latest_input = req.payload
    workspace.latest_output = output
    workspace.last_synced_at = req.payload.period_end
    return output


@app.get("/dashboard/{buyer_id}/latest", response_model=CannabisOutput)
def dashboard_latest(buyer_id: str) -> CannabisOutput:
    workspace = store.get_or_create(buyer_id)
    if not workspace.latest_output:
        raise HTTPException(status_code=404, detail="No analysis available for this buyer.")
    return workspace.latest_output


@app.get("/dashboard/{buyer_id}/kpis")
def dashboard_kpis(buyer_id: str):
    workspace = store.get_or_create(buyer_id)
    if not workspace.latest_input or not workspace.latest_output:
        raise HTTPException(status_code=404, detail="No KPI data available for this buyer.")

    i = workspace.latest_input
    o = workspace.latest_output
    return {
        "buyer_id": buyer_id,
        "period": {"start": str(i.period_start), "end": str(i.period_end)},
        "state": i.state,
        "sales": {
            "total_sales_usd": i.total_sales_usd,
            "transactions": i.transactions,
            "units_sold": i.units_sold,
            "avg_basket_usd": i.avg_basket_usd,
        },
        "risk": {
            "score": o.score,
            "tier": o.tier,
            "market_pressure": o.market_pressure,
            "compliance_risk": o.compliance_risk,
            "inventory_stress": o.inventory_stress,
        },
        "regulation_links": o.regulation_links,
    }


@app.get("/dashboard/{buyer_id}/recommendations")
def dashboard_recommendations(buyer_id: str):
    workspace = store.get_or_create(buyer_id)
    if not workspace.latest_output:
        raise HTTPException(status_code=404, detail="No recommendation data available for this buyer.")
    return {
        "buyer_id": buyer_id,
        "recommendations": workspace.latest_output.recommendations,
    }


@app.get("/dashboard/buyers")
def dashboard_buyers() -> dict[str, list[str]]:
    return {"buyers": store.list_buyers()}
