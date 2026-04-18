from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from doobielogic.copilot import DoobieCopilot
from doobielogic.evals import apply_low_confidence_fallback
from doobielogic.intelligence_v3 import build_intel_v3
from doobielogic.key_management import KeyStore
from doobielogic.learning_store_v1 import log_event, summarize_learning
from doobielogic.license_store import LicenseStore

app = FastAPI(title="DoobieLogic API v4")

API_KEY = os.environ.get("DOOBIE_API_KEY", "")
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
LICENSE_STORE = LicenseStore(path=os.environ.get("DOOBIE_LICENSE_STORE", "data/license_store.json"))
KEY_STORE = KeyStore(path=os.environ.get("DOOBIE_KEY_DB", "data/key_store.db"))
KEY_VALIDATION_TOKEN = os.environ.get("DOOBIE_KEY_VALIDATION_TOKEN", "")
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


class LicenseValidateReq(BaseModel):
    license_key: str


class CustomerCreateReq(BaseModel):
    company_name: str
    contact_name: str
    contact_email: str
    notes: str = ""


class LicenseGenerateReq(BaseModel):
    customer_id: str
    plan_type: str
    expires_at: str | None = None


class LicenseRevokeReq(BaseModel):
    license_key: str
    revoked_reason: str | None = None


class LicenseResetReq(BaseModel):
    license_key: str
    reason: str | None = None


class ApiKeyValidateReq(BaseModel):
    api_key: str


def _parse_bearer(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    prefix = "bearer "
    safe = auth_header.strip()
    if safe.lower().startswith(prefix):
        return safe[len(prefix) :].strip()
    return None


def _resolve_service_key(x_api_key: str | None, authorization: str | None) -> str | None:
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    return _parse_bearer(authorization)


def require_service_auth(
    *,
    x_api_key: str | None,
    authorization: str | None,
    required_scope: str | None = None,
) -> None:
    """Authenticate service access using x-api-key or Authorization Bearer token.

    Supported styles:
    - x-api-key: <DOOBIE_API_KEY>
    - Authorization: Bearer <DOOBIE_API_KEY>
    """
    if not x_api_key and authorization and _parse_bearer(authorization) is None:
        raise HTTPException(status_code=401, detail="Invalid Authorization header format. Use 'Bearer <service-key>'.")

    key = _resolve_service_key(x_api_key, authorization)
    safe_key = (key or "").strip()

    if API_KEY and safe_key == API_KEY:
        return

    if not API_KEY and not safe_key:
        return

    if not safe_key:
        raise HTTPException(
            status_code=401,
            detail="Missing service API key. Provide x-api-key or Authorization: Bearer <service-key>.",
        )

    result = KEY_STORE.validate_api_key(safe_key)
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid service API key.")

    if required_scope:
        scopes = set(result.get("permissions") or [])
        if required_scope not in scopes and "admin" not in scopes:
            raise HTTPException(status_code=403, detail=f"Missing scope: {required_scope}")


def admin_auth(authorization: str | None) -> None:
    token = _parse_bearer(authorization)
    if ADMIN_API_KEY and token != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _support_response(resp, mode: str) -> dict[str, Any]:
    standard = {
        "answer": resp.answer,
        "explanation": resp.explanation,
        "recommendations": resp.recommendations,
        "confidence": resp.confidence,
        "sources": resp.sources,
        "mode": mode,
        "risk_flags": resp.risk_flags,
        "inefficiencies": resp.inefficiencies,
    }
    return apply_low_confidence_fallback(standard)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "DoobieLogic API v4",
        "license_validation_route": "/api/v1/license/validate",
    }


@app.post("/buyer/intelligence")
def buyer(req: BuyerReq, x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    require_service_auth(x_api_key=x_api_key, authorization=authorization, required_scope="buyer_dashboard")
    return build_intel_v3(req.question, req.inventory, "buyer", req.state)


@app.post("/extraction/intelligence")
def extraction(req: ExtractionReq, x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    require_service_auth(x_api_key=x_api_key, authorization=authorization, required_scope="buyer_dashboard")
    return build_intel_v3(req.question, req.run_data, "extraction", req.state)


@app.post("/learning/feedback")
def learning(req: LearnReq, x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    require_service_auth(x_api_key=x_api_key, authorization=authorization, required_scope="buyer_dashboard")
    return log_event(**req.model_dump())


@app.get("/learning/summary")
def learning_summary(x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    require_service_auth(x_api_key=x_api_key, authorization=authorization, required_scope="buyer_dashboard")
    return summarize_learning()


@app.post("/api/v1/support/buyer_brief")
def support_buyer_brief(req: SupportReq, x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_service_auth(x_api_key=x_api_key, authorization=authorization, required_scope="buyer_dashboard")
    resp = COPILOT.ask_with_buyer_brain(req.question, mapped_data=req.data, persona="buyer", state=req.state)
    return _support_response(resp, mode="buyer")


@app.post("/api/v1/support/inventory_check")
def support_inventory_check(req: SupportReq, x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_service_auth(x_api_key=x_api_key, authorization=authorization, required_scope="buyer_dashboard")
    resp = COPILOT.ask_with_buyer_brain(req.question, mapped_data=req.data, persona="buyer", state=req.state)
    return _support_response(resp, mode="inventory")


@app.post("/api/v1/support/extraction_brief")
def support_extraction_brief(req: SupportReq, x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_service_auth(x_api_key=x_api_key, authorization=authorization, required_scope="buyer_dashboard")
    resp = COPILOT.ask_with_operations(req.question, department="extraction", parsed_data=req.data, persona="extraction", state=req.state)
    return _support_response(resp, mode="extraction")


@app.post("/api/v1/support/ops_brief")
def support_ops_brief(req: SupportReq, x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_service_auth(x_api_key=x_api_key, authorization=authorization, required_scope="buyer_dashboard")
    department = (req.department or "operations").lower()
    resp = COPILOT.ask_with_operations(req.question, department=department, parsed_data=req.data, persona="ops", state=req.state)
    return _support_response(resp, mode="ops")


@app.post("/api/v1/support/copilot")
def support_copilot(req: SupportReq, x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_service_auth(x_api_key=x_api_key, authorization=authorization, required_scope="buyer_dashboard")
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


@app.post("/api/v1/license/validate")
def validate_license(req: LicenseValidateReq, x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_service_auth(x_api_key=x_api_key, authorization=authorization, required_scope="buyer_dashboard")
    return LICENSE_STORE.validate_license(req.license_key)


@app.post("/api/v1/keys/validate")
def validate_key(req: ApiKeyValidateReq, x_validation_token: str | None = Header(default=None)) -> dict[str, Any]:
    if KEY_VALIDATION_TOKEN and x_validation_token != KEY_VALIDATION_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return KEY_STORE.validate_api_key(req.api_key)


@app.post("/api/v1/admin/customers")
def admin_create_customer(req: CustomerCreateReq, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    admin_auth(authorization)
    customer = LICENSE_STORE.create_customer(
        company_name=req.company_name,
        contact_name=req.contact_name,
        contact_email=req.contact_email,
        notes=req.notes,
    )
    return customer.to_dict()


@app.get("/api/v1/admin/customers")
def admin_list_customers(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    admin_auth(authorization)
    customers = [c.to_dict() for c in LICENSE_STORE.list_customers()]
    return {"customers": customers}


@app.post("/api/v1/admin/licenses/generate")
def admin_generate_license(req: LicenseGenerateReq, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    admin_auth(authorization)
    try:
        license_obj = LICENSE_STORE.create_license(req.customer_id, req.plan_type, expires_at=req.expires_at)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return license_obj.to_dict()


@app.get("/api/v1/admin/licenses")
def admin_list_licenses(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    admin_auth(authorization)
    licenses = [l.to_dict() for l in LICENSE_STORE.list_licenses()]
    return {"licenses": licenses}


@app.post("/api/v1/admin/licenses/revoke")
def admin_revoke_license(req: LicenseRevokeReq, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    admin_auth(authorization)
    try:
        license_obj = LICENSE_STORE.revoke_license(req.license_key, reason=req.revoked_reason)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return license_obj.to_dict()


@app.post("/api/v1/admin/licenses/reset")
def admin_reset_license(req: LicenseResetReq, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    admin_auth(authorization)
    try:
        result = LICENSE_STORE.reset_license(req.license_key, reason=req.reason)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"old_license": result["old"].to_dict(), "new_license": result["new"].to_dict()}
