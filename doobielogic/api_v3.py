from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Any
import os

from doobielogic.intelligence_v2 import build_intel

app = FastAPI(title="DoobieLogic API v3")

API_KEY = os.environ.get("DOOBIELOGIC_API_KEY", "")

class BuyerReq(BaseModel):
    question: str
    state: str | None = None
    inventory: dict[str, Any] = {}

class ExtractionReq(BaseModel):
    question: str
    state: str | None = None
    run_data: dict[str, Any] = {}


def auth(key: str | None):
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.post("/buyer/intelligence")
def buyer(req: BuyerReq, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    return build_intel(req.question, req.inventory, "buyer", req.state)

@app.post("/extraction/intelligence")
def extraction(req: ExtractionReq, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    return build_intel(req.question, req.run_data, "extraction", req.state)
