from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from doobielogic.copilot import DoobieCopilot
from doobielogic.evals import apply_low_confidence_fallback
from doobielogic.intelligence_v3 import build_intel_v3
from doobielogic.learning_store_v1 import log_event, summarize_learning

app = FastAPI(title="DoobieLogic API v4")

API_KEY = os.environ.get("DOOBIE_API_KEY", "")
COPILOT = DoobieCopilot()


class BuyerReq(BaseModel):
    question: str
    state: str | None = None
    inventory: dict[str, Any] = Field(default_factory=dict)


class ExtractionReq(BaseModel):
    question: str
    state: str | None = None
    run_data: dict[str, Any] = Field(default_factory=dict)


class LearnReq(BaseModel):
    mode: str
    question: str
    state: str | None = None
    outcome: str
    recommendation: str | None = None


class SupportReq(BaseModel):
    question: str
    state: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    mode: str | None = None
    department: str | None = None
    persona: str | None = None


def auth(key: str | None) -> None:
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _support_response(resp, mode: str) -> dict[str, Any]:
    standard = {
        "answer": resp.answer,
        "explanation": resp.explanation,
        "recommendations": resp.recommendations,
        "confidence": resp.confidence,
        "sources": resp.sources,
        "mode": mode,
    }
    return apply_low_confidence_fallback(standard)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/buyer/intelligence")
def buyer(req: BuyerReq, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    return build_intel_v3(req.question, req.inventory, "buyer", req.state)


@app.post("/extraction/intelligence")
def extraction(req: ExtractionReq, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    return build_intel_v3(req.question, req.run_data, "extraction", req.state)


@app.post("/learning/feedback")
def learning(req: LearnReq, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    return log_event(**req.model_dump())


@app.get("/learning/summary")
def learning_summary(x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    return summarize_learning()


@app.post("/api/v1/support/buyer_brief")
def support_buyer_brief(req: SupportReq, x_api_key: str | None = Header(default=None)) -> dict[str, Any]:
    auth(x_api_key)
    resp = COPILOT.ask_with_buyer_brain(req.question, mapped_data=req.data, persona="buyer", state=req.state)
    return _support_response(resp, mode="buyer")


@app.post("/api/v1/support/inventory_check")
def support_inventory_check(req: SupportReq, x_api_key: str | None = Header(default=None)) -> dict[str, Any]:
    auth(x_api_key)
    resp = COPILOT.ask_with_buyer_brain(req.question, mapped_data=req.data, persona="buyer", state=req.state)
    return _support_response(resp, mode="inventory")


@app.post("/api/v1/support/extraction_brief")
def support_extraction_brief(req: SupportReq, x_api_key: str | None = Header(default=None)) -> dict[str, Any]:
    auth(x_api_key)
    resp = COPILOT.ask_with_operations(req.question, department="extraction", parsed_data=req.data, persona="extraction", state=req.state)
    return _support_response(resp, mode="extraction")


@app.post("/api/v1/support/ops_brief")
def support_ops_brief(req: SupportReq, x_api_key: str | None = Header(default=None)) -> dict[str, Any]:
    auth(x_api_key)
    department = (req.department or "operations").lower()
    resp = COPILOT.ask_with_operations(req.question, department=department, parsed_data=req.data, persona="ops", state=req.state)
    return _support_response(resp, mode="ops")


@app.post("/api/v1/support/copilot")
def support_copilot(req: SupportReq, x_api_key: str | None = Header(default=None)) -> dict[str, Any]:
    auth(x_api_key)
    mode = (req.mode or req.persona or "buyer").lower()

    if mode in {"buyer", "inventory"}:
        resp = COPILOT.ask_with_buyer_brain(req.question, mapped_data=req.data, persona="buyer", state=req.state)
        return _support_response(resp, mode=mode)
    if mode == "extraction":
        resp = COPILOT.ask_with_operations(req.question, department="extraction", parsed_data=req.data, persona="extraction", state=req.state)
        return _support_response(resp, mode="extraction")
    if mode in {"ops", "operations"}:
        dept = (req.department or "operations").lower()
        resp = COPILOT.ask_with_operations(req.question, department=dept, parsed_data=req.data, persona="ops", state=req.state)
        return _support_response(resp, mode="ops")

    routed_persona = "compliance" if mode == "compliance" else "executive"
    resp = COPILOT.ask(req.question, persona=routed_persona, state=req.state)
    return _support_response(resp, mode=routed_persona)
