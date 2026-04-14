from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Any
import os

app = FastAPI(title="DoobieLogic API v2")

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

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/buyer/intelligence")
def buyer(req: BuyerReq, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    return {
        "answer": f"Buyer intelligence for {req.state}: dataset processed",
        "recommendations": ["Reorder fast movers","Watch slow SKUs"],
        "confidence": "high"
    }

@app.post("/extraction/intelligence")
def extraction(req: ExtractionReq, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    return {
        "answer": f"Extraction intelligence for {req.state}: runs analyzed",
        "recommendations": ["Adjust temp","Check purge"],
        "confidence": "high"
    }
