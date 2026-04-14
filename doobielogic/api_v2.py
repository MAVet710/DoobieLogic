from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from doobielogic.intelligence_v2 import build_unified_intelligence


app = FastAPI(title="DoobieLogic API v2", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _expected_api_key() -> str:
    return os.environ.get("DOOBIELOGIC_API_KEY", "").strip()


def _authorize(x_api_key: str | None) -> None:
    expected = _expected_api_key()
    if not expected:
        return
    if not x_api_key or x_api_key.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


class BuyerIntelligenceRequest(BaseModel):
    question: str = Field(min_length=1)
    state: str | None = Field(default=None)
    inventory: dict[str, Any] = Field(default_factory=dict)
    focus: str = Field(default="buyer")


class ExtractionIntelligenceRequest(BaseModel):
    question: str = Field(min_length=1)
    state: str | None = Field(default=None)
    run_data: dict[str, Any] = Field(default_factory=dict)
    focus: str = Field(default="extraction")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "DoobieLogic API v2"}


@app.post("/buyer/intelligence")
def buyer_intelligence(req: BuyerIntelligenceRequest, x_api_key: str | None = Header(default=None)) -> dict[str, Any]:
    _authorize(x_api_key)
    result = build_unified_intelligence(
        question=req.question,
        mapped_data=req.inventory,
        persona="buyer",
        state=req.state,
    )
    return {
        "focus": req.focus,
        "state": req.state.upper() if isinstance(req.state, str) else None,
        "answer": result.get("answer", ""),
        "buyer_signals": result.get("buyer_signals", {}),
        "compliance_flags": result.get("public_context", {}),
        "recommendations": result.get("recommendations", []),
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", "low"),
        "grounding": result.get("grounding", ""),
    }


@app.post("/extraction/intelligence")
def extraction_intelligence(req: ExtractionIntelligenceRequest, x_api_key: str | None = Header(default=None)) -> dict[str, Any]:
    _authorize(x_api_key)
    result = build_unified_intelligence(
        question=req.question,
        mapped_data=req.run_data,
        persona="extraction",
        state=req.state,
    )
    return {
        "focus": req.focus,
        "state": req.state.upper() if isinstance(req.state, str) else None,
        "answer": result.get("answer", ""),
        "extraction_ops": result.get("extraction_ops", {}),
        "extraction_science": result.get("extraction_science", {}),
        "public_context": result.get("public_context", {}),
        "recommendations": result.get("recommendations", []),
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", "low"),
        "grounding": result.get("grounding", ""),
    }
