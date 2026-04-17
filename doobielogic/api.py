from __future__ import annotations

from datetime import date
import os

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .copilot import DoobieCopilot
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
copilot = DoobieCopilot()
API_KEY = os.environ.get("DOOBIE_API_KEY", "")


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


class SupportResponse(BaseModel):
    answer: str
    explanation: str
    recommendations: list[str]
    confidence: str
    sources: list[str]
    mode: str


class BuyerBriefRequest(BaseModel):
    question: str | None = None
    state: str | None = None
    data: dict = Field(default_factory=dict)


class InventoryCheckRequest(BaseModel):
    question: str | None = None
    state: str | None = None
    data: dict = Field(default_factory=dict)


class ExtractionBriefRequest(BaseModel):
    question: str | None = None
    state: str | None = None
    data: dict = Field(default_factory=dict)


class OpsBriefRequest(BaseModel):
    question: str | None = None
    state: str | None = None
    department: str | None = None
    data: dict = Field(default_factory=dict)


class CopilotSupportRequest(BaseModel):
    question: str
    persona: str | None = None
    state: str | None = None
    data: dict = Field(default_factory=dict)


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    if not API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization[len("Bearer ") :].strip()
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _support_response(result, mode: str) -> SupportResponse:
    return SupportResponse(
        answer=result.answer,
        explanation=result.explanation,
        recommendations=result.recommendations,
        confidence=result.confidence,
        sources=result.sources,
        mode=mode,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "DoobieLogic", "version": app.version}


@app.get("/states")
def states(_: None = Depends(require_api_key)) -> dict[str, dict[str, str]]:
    return REGULATION_LINKS


@app.post("/analyze", response_model=CannabisOutput)
def analyze(payload: CannabisInput, _: None = Depends(require_api_key)) -> CannabisOutput:
    if payload.state not in REGULATION_LINKS:
        raise HTTPException(status_code=400, detail=f"Unsupported state code: {payload.state}")
    return engine.analyze(payload)


@app.post("/sales/ingest")
def sales_ingest(req: SalesIngestRequest, _: None = Depends(require_api_key)):
    rows = sales_client.fetch_sales(req.state.upper(), str(req.start_date), str(req.end_date))
    return {"state": req.state.upper(), "rows": len(rows), "preview": rows[:3]}


@app.post("/dashboard/{buyer_id}/sync")
def dashboard_sync(buyer_id: str, req: DashboardSyncRequest, _: None = Depends(require_api_key)):
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
def dashboard_analyze_store(req: DashboardAnalyzeRequest, _: None = Depends(require_api_key)) -> CannabisOutput:
    output = analyze(req.payload)
    workspace = store.get_or_create(req.buyer_id)
    workspace.latest_input = req.payload
    workspace.latest_output = output
    workspace.last_synced_at = req.payload.period_end
    return output


@app.get("/dashboard/{buyer_id}/latest", response_model=CannabisOutput)
def dashboard_latest(buyer_id: str, _: None = Depends(require_api_key)) -> CannabisOutput:
    workspace = store.get_or_create(buyer_id)
    if not workspace.latest_output:
        raise HTTPException(status_code=404, detail="No analysis available for this buyer.")
    return workspace.latest_output


@app.get("/dashboard/{buyer_id}/kpis")
def dashboard_kpis(buyer_id: str, _: None = Depends(require_api_key)):
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
def dashboard_recommendations(buyer_id: str, _: None = Depends(require_api_key)):
    workspace = store.get_or_create(buyer_id)
    if not workspace.latest_output:
        raise HTTPException(status_code=404, detail="No recommendation data available for this buyer.")
    return {
        "buyer_id": buyer_id,
        "recommendations": workspace.latest_output.recommendations,
    }


@app.get("/dashboard/buyers")
def dashboard_buyers(_: None = Depends(require_api_key)) -> dict[str, list[str]]:
    return {"buyers": store.list_buyers()}


@app.get("/api/v1/auth/check")
def auth_check(_: None = Depends(require_api_key)) -> dict[str, str | bool]:
    return {"authenticated": True, "service": "DoobieLogic"}


@app.post("/api/v1/support/buyer_brief", response_model=SupportResponse)
def support_buyer_brief(req: BuyerBriefRequest, _: None = Depends(require_api_key)) -> SupportResponse:
    result = copilot.ask_with_buyer_brain(req.question or "Provide buyer brief", mapped_data=req.data, persona="buyer", state=req.state)
    return _support_response(result, mode="buyer")


@app.post("/api/v1/support/inventory_check", response_model=SupportResponse)
def support_inventory_check(req: InventoryCheckRequest, _: None = Depends(require_api_key)) -> SupportResponse:
    result = copilot.ask_with_buyer_brain(req.question or "Provide inventory check", mapped_data=req.data, persona="buyer", state=req.state)
    return _support_response(result, mode="inventory")


@app.post("/api/v1/support/extraction_brief", response_model=SupportResponse)
def support_extraction_brief(req: ExtractionBriefRequest, _: None = Depends(require_api_key)) -> SupportResponse:
    result = copilot.ask_with_operations(req.question or "Provide extraction brief", department="extraction", parsed_data=req.data, persona="extraction", state=req.state)
    return _support_response(result, mode="extraction")


@app.post("/api/v1/support/ops_brief", response_model=SupportResponse)
def support_ops_brief(req: OpsBriefRequest, _: None = Depends(require_api_key)) -> SupportResponse:
    department = (req.department or "operations").lower()
    result = copilot.ask_with_operations(req.question or "Provide operations brief", department=department, parsed_data=req.data, persona="ops", state=req.state)
    return _support_response(result, mode="ops")


@app.post("/api/v1/support/copilot", response_model=SupportResponse)
def support_copilot(req: CopilotSupportRequest, _: None = Depends(require_api_key)) -> SupportResponse:
    persona = (req.persona or "buyer").lower()
    if persona in {"buyer", "inventory"}:
        result = copilot.ask_with_buyer_brain(req.question, mapped_data=req.data, persona="buyer", state=req.state)
        return _support_response(result, mode=persona)
    if persona == "extraction":
        result = copilot.ask_with_operations(req.question, department="extraction", parsed_data=req.data, persona="extraction", state=req.state)
        return _support_response(result, mode="extraction")
    if persona in {"ops", "operations"}:
        result = copilot.ask_with_operations(req.question, department="operations", parsed_data=req.data, persona="ops", state=req.state)
        return _support_response(result, mode="ops")
    routed = "compliance" if persona == "compliance" else "executive"
    result = copilot.ask(req.question, persona=routed, state=req.state)
    return _support_response(result, mode=routed)
