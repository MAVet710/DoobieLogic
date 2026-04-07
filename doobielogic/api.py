from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from doobielogic.assistant import CannabisOpsAssistant
from doobielogic.community import CommunityAnswer, CommunityStore, VerificationReport, new_answer_id, now_iso
from doobielogic.dashboard import BuyerWorkspaceStore
from doobielogic.engine import CannabisLogicEngine
from doobielogic.models import CannabisInput, CannabisOutput
from doobielogic.knowledge import CannabisKnowledgeBase
from doobielogic.normalizer import normalize_sales_rows_to_input
from doobielogic.regulations import REGULATION_LINKS
from doobielogic.sales_api import CannabisSalesAPIClient
from doobielogic.verification import verify_sources

app = FastAPI(title="DoobieLogic", version="0.3.0")
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
community_store = CommunityStore()
knowledge_base = CannabisKnowledgeBase()
assistant = CannabisOpsAssistant(knowledge_base)


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


class CommunityQuestionCreateRequest(BaseModel):
    asked_by: str = Field(min_length=1)
    role: str = Field(pattern="^(buyer|operator|compliance|analyst|other)$")
    state: str = Field(min_length=2, max_length=2)
    question_text: str = Field(min_length=10)
    tags: list[str] = Field(default_factory=list)


class CommunityAnswerCreateRequest(BaseModel):
    responder_role: str = Field(pattern="^(buyer|operator|compliance|analyst|other)$")
    answer_text: str = Field(min_length=20)
    sources: list[str] = Field(default_factory=list)


class KnowledgeAskRequest(BaseModel):
    question: str = Field(min_length=5)
    limit: int = Field(default=5, ge=1, le=10)


class ChatMessageRequest(BaseModel):
    question: str = Field(min_length=5)
    persona: str = Field(default="buyer", pattern="^(buyer|sales|cultivation|extraction|operations)$")
    limit: int = Field(default=5, ge=1, le=10)


class ChatFeedbackRequest(BaseModel):
    persona: str = Field(default="buyer", pattern="^(buyer|sales|cultivation|extraction|operations)$")
    question: str = Field(min_length=5)
    answer: str = Field(min_length=10)
    helpful: bool


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


@app.post("/community/questions")
def create_community_question(req: CommunityQuestionCreateRequest):
    if req.state.upper() not in REGULATION_LINKS:
        raise HTTPException(status_code=400, detail=f"Unsupported state code: {req.state.upper()}")
    question = community_store.create_question(req.asked_by, req.role, req.state, req.question_text, req.tags)
    return question


@app.get("/community/questions")
def list_community_questions(state: str | None = None, tag: str | None = None):
    return community_store.list_questions(state=state, tag=tag)


@app.get("/community/questions/{question_id}")
def get_community_question(question_id: str):
    question = community_store.get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@app.post("/community/questions/{question_id}/answers")
def add_community_answer(question_id: str, req: CommunityAnswerCreateRequest):
    verified, trusted, untrusted = verify_sources(req.sources)

    if not verified:
        raise HTTPException(
            status_code=400,
            detail="Answer rejected: include at least one trusted verification source (.gov/.edu or approved cannabis regulator domain).",
        )

    report = VerificationReport(
        verified=verified,
        trusted_sources=trusted,
        untrusted_sources=untrusted,
        checked_at=now_iso(),
        notes="Automated source-domain verification passed. Use human compliance review for policy-critical answers.",
    )
    answer = CommunityAnswer(
        answer_id=new_answer_id(),
        responder_role=req.responder_role,
        answer_text=req.answer_text,
        sources=req.sources,
        verification=report,
        created_at=now_iso(),
    )

    updated = community_store.add_answer(question_id, answer)
    if not updated:
        raise HTTPException(status_code=404, detail="Question not found")

    return {
        "question_id": question_id,
        "answer_id": answer.answer_id,
        "verification": report,
        "answer": answer,
    }


@app.get("/knowledge/categories")
def knowledge_categories() -> dict[str, list[str]]:
    return {"categories": knowledge_base.categories()}


@app.post("/knowledge/ask")
def knowledge_ask(req: KnowledgeAskRequest):
    return knowledge_base.ask(req.question, req.limit)


@app.post("/chat/message")
def chat_message(req: ChatMessageRequest):
    resp = assistant.chat(req.question, req.persona, req.limit)
    return {
        "question": req.question,
        "persona": req.persona,
        "answer": resp.answer,
        "citations": resp.citations,
        "suggested_actions": resp.suggested_actions,
    }


@app.post("/chat/feedback")
def chat_feedback(req: ChatFeedbackRequest):
    knowledge_base.learn_from_feedback(req.persona, req.question, req.answer, req.helpful)
    return {"status": "stored", "helpful": req.helpful}
