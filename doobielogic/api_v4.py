from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Any
import os

from doobielogic.intelligence_v3 import build_intel_v3
from doobielogic.learning_store_v1 import log_event, summarize_learning

app = FastAPI(title="DoobieLogic API v4")

API_KEY = os.environ.get("DOOBIELOGIC_API_KEY", "")

class BuyerReq(BaseModel):
    question: str
    state: str | None = None
    inventory: dict[str, Any] = {}

class ExtractionReq(BaseModel):
    question: str
    state: str | None = None
    run_data: dict[str, Any] = {}

class LearnReq(BaseModel):
    mode: str
    question: str
    state: str | None = None
    outcome: str
    recommendation: str | None = None


def auth(key: str | None):
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

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
    return log_event(**req.dict())

@app.get("/learning/summary")
def learning_summary(x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    return summarize_learning()
