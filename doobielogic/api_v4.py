from __future__ import annotations

import os
from base64 import b64decode
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from doobielogic.copilot import DoobieCopilot
from doobielogic.config import load_doobie_config
from doobielogic.evals import apply_low_confidence_fallback
from doobielogic.intelligence_v3 import build_intel_v3
from doobielogic.admin_auth import load_admin_auth_config, verify_admin_credentials
from doobielogic.key_management import KEY_ROLE_ADMIN, KEY_ROLE_SERVICE, KeyStore
from doobielogic.learning_store_v1 import log_event, summarize_learning
from doobielogic.license_store import LicenseStore

app = FastAPI(title="DoobieLogic API v4")

CONFIG = load_doobie_config()
API_KEY = CONFIG.api_key
ADMIN_API_KEY = CONFIG.admin_api_key
LICENSE_STORE = LicenseStore(path=CONFIG.license_store_path, database_url=CONFIG.database_url)
KEY_STORE = KeyStore(path=CONFIG.key_store_path, database_url=CONFIG.database_url)
KEY_VALIDATION_TOKEN = CONFIG.key_validation_token
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


class ApiKeyGenerateReq(BaseModel):
    company_name: str
    label: str
    scope: str
    expires_at: str | None = None
    notes: str = ""


class AdminBootstrapGenerateReq(BaseModel):
    label: str = "Initial Bootstrap Admin Key"
    notes: str = ""


class AdminApiKeyGenerateReq(BaseModel):
    label: str
    expires_at: str | None = None
    notes: str = ""


class ApiKeyRecordReq(BaseModel):
    record_id: str


class ApiKeyStatusReq(BaseModel):
    record_id: str
    is_active: bool


class ApiKeyUpdateReq(BaseModel):
    record_id: str
    expires_at: str | None = None
    notes: str | None = None
    tier_or_scope: str | None = None
    label: str | None = None
    max_users: int | None = None
    trial: bool | None = None


def _parse_bearer(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    prefix = "bearer "
    safe = auth_header.strip()
    if safe.lower().startswith(prefix):
        return safe[len(prefix) :].strip()
    return None


def _parse_basic(auth_header: str | None) -> tuple[str, str] | None:
    if not auth_header:
        return None
    safe = auth_header.strip()
    prefix = "basic "
    if not safe.lower().startswith(prefix):
        return None
    encoded = safe[len(prefix) :].strip()
    if not encoded:
        return None
    try:
        decoded = b64decode(encoded).decode("utf-8")
    except Exception:
        return None
    if ":" not in decoded:
        return None
    username, password = decoded.split(":", 1)
    return username, password


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

    result = KEY_STORE.validate_api_key(safe_key, expected_role=KEY_ROLE_SERVICE)
    if not result.get("valid"):
        reason = str(result.get("reason") or "invalid")
        if reason == "not_found":
            raise HTTPException(
                status_code=401,
                detail="Invalid service API key (not found in active key store). This can indicate storage mismatch across deployments.",
            )
        raise HTTPException(status_code=401, detail=f"Invalid service API key ({reason}).")

    if required_scope:
        scopes = set(result.get("permissions") or [])
        if required_scope not in scopes and "admin" not in scopes:
            raise HTTPException(status_code=403, detail=f"Missing scope: {required_scope}")


def admin_auth(authorization: str | None) -> None:
    token = _parse_bearer(authorization)
    if not token:
        basic = _parse_basic(authorization)
        if not basic:
            raise HTTPException(status_code=401, detail="Unauthorized")
        username, password = basic
        auth_cfg = load_admin_auth_config(secrets=None, env=os.environ)
        if verify_admin_credentials(username=username, password=password, config=auth_cfg):
            return
        raise HTTPException(status_code=401, detail="Unauthorized")
    if ADMIN_API_KEY and token == ADMIN_API_KEY:
        return
    result = KEY_STORE.validate_admin_key(token)
    if not result.get("valid"):
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
    diagnostics = CONFIG.diagnostics()
    license_diag = LICENSE_STORE.diagnostic()
    key_diag = KEY_STORE.diagnostic()
    postgres_reachable = (
        license_diag.get("postgres_reachable") == "true"
        and key_diag.get("postgres_reachable") == "true"
        if diagnostics["database_url_configured"]
        else False
    )
    source_of_truth = "postgres_shared" if (license_diag.get("backend") == "postgres" and key_diag.get("backend") == "postgres") else "local_legacy"
    warnings = list(diagnostics["warnings"])
    if source_of_truth == "local_legacy" and diagnostics.get("production_like_env"):
        warnings.append("Keys and licenses are deployment-local and may not survive redeploys.")
    return {
        "status": "ok",
        "service": "DoobieLogic API v4",
        "license_validation_route": "/api/v1/license/validate",
        "backend_mode": str(diagnostics["backend_mode"]),
        "backend_mode_source": str(diagnostics["backend_mode_source"]),
        "preferred_backend_mode": str(diagnostics["preferred_backend_mode"]),
        "license_store": str(diagnostics["license_store_path"]),
        "key_store": str(diagnostics["key_store_path"]),
        "license_store_backend": str(license_diag.get("backend")),
        "key_store_backend": str(key_diag.get("backend")),
        "postgres_configured": "true" if bool(diagnostics["database_url_configured"]) else "false",
        "database_url_source": str(diagnostics.get("database_url_source") or ""),
        "postgres_reachable": "true" if postgres_reachable else "false",
        "source_of_truth": source_of_truth,
        "warnings": ",".join(dict.fromkeys(warnings)) if warnings else "",
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
    if mode in {"retail_ops", "cultivation", "kitchen", "packaging"}:
        resp = COPILOT.ask_with_operations(
            req.question,
            department=mode,
            parsed_data=req.data,
            persona=mode,  # type: ignore[arg-type]
            state=req.state,
        )
        return _support_response(resp, mode=mode)
    if mode == "compliance":
        resp = COPILOT.ask_with_operations(
            req.question,
            department="compliance",
            parsed_data=req.data,
            persona="compliance",
            state=req.state,
        )
        return _support_response(resp, mode="compliance")

    resp = COPILOT.ask(req.question, persona="executive", state=req.state)
    routed_persona = "executive"
    return _support_response(resp, mode=routed_persona)


@app.post("/api/v1/license/validate")
def validate_license(req: LicenseValidateReq, x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_service_auth(x_api_key=x_api_key, authorization=authorization, required_scope="buyer_dashboard")
    result = LICENSE_STORE.validate_license(req.license_key)
    if not result.get("valid") and result.get("reason") == "not_found":
        result["diagnostic"] = "license_not_found_in_active_store"
    return result


@app.post("/api/v1/keys/validate")
def validate_key(req: ApiKeyValidateReq, x_validation_token: str | None = Header(default=None)) -> dict[str, Any]:
    if KEY_VALIDATION_TOKEN and x_validation_token != KEY_VALIDATION_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return KEY_STORE.validate_api_key(req.api_key)


@app.post("/api/v1/admin/licenses/validate")
def admin_validate_license(req: LicenseValidateReq, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    admin_auth(authorization)
    result = LICENSE_STORE.validate_license(req.license_key)
    if not result.get("valid") and result.get("reason") == "not_found":
        result["diagnostic"] = "license_not_found_in_active_store"
    return result


@app.get("/api/v1/admin/diagnostics/storage")
def admin_storage_diagnostics(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    admin_auth(authorization)
    key_diag = KEY_STORE.diagnostic()
    license_diag = LICENSE_STORE.diagnostic()
    source_of_truth = "postgres_shared" if (license_diag.get("backend") == "postgres" and key_diag.get("backend") == "postgres") else "local_legacy"

    service_keys = KEY_STORE.load_key_records(key_type="api", key_role=KEY_ROLE_SERVICE)
    admin_keys = KEY_STORE.load_key_records(key_type="api", key_role=KEY_ROLE_ADMIN)
    licenses = LICENSE_STORE.list_licenses()

    active_service_key_count = sum(1 for row in service_keys if bool(row.get("is_active", True)) and not bool(row.get("is_revoked", False)))
    active_admin_key_count = sum(1 for row in admin_keys if bool(row.get("is_active", True)) and not bool(row.get("is_revoked", False)))
    active_license_count = sum(1 for lic in licenses if str(getattr(lic, "status", "")).lower() == "active")

    return {
        "key_store_backend": str(key_diag.get("backend")),
        "license_store_backend": str(license_diag.get("backend")),
        "source_of_truth": source_of_truth,
        "active_service_key_count": active_service_key_count,
        "active_admin_key_count": active_admin_key_count,
        "active_license_count": active_license_count,
    }


@app.get("/api/v1/admin/bootstrap/status")
def admin_bootstrap_status() -> dict[str, Any]:
    has_admin_key = KEY_STORE.has_active_admin_key()
    return {
        "bootstrap_mode": not has_admin_key,
        "admin_api_key_configured": bool(ADMIN_API_KEY),
        "admin_key_source": "env" if ADMIN_API_KEY else ("key_store" if has_admin_key else "none"),
    }


@app.post("/api/v1/admin/bootstrap/generate")
def admin_bootstrap_generate(req: AdminBootstrapGenerateReq) -> dict[str, Any]:
    if ADMIN_API_KEY:
        raise HTTPException(status_code=409, detail="Bootstrap disabled: ADMIN_API_KEY env is already configured")
    if KEY_STORE.has_active_admin_key():
        raise HTTPException(status_code=409, detail="Bootstrap disabled: an admin API key already exists")
    generated = KEY_STORE.create_admin_api_key(label=req.label, notes=req.notes, is_bootstrap=True)
    return {"record_id": generated.record_id, "raw_key": generated.raw_key, "key_preview": generated.key_preview}

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


@app.post("/api/v1/admin/api-keys/generate")
def admin_generate_api_key(req: ApiKeyGenerateReq, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    admin_auth(authorization)
    generated = KEY_STORE.create_api_key(
        company_name=req.company_name,
        label=req.label,
        scope=req.scope,
        expiration_date=None,
        notes=req.notes,
    )
    if req.expires_at:
        KEY_STORE.update_key_metadata(generated.record_id, expires_at=req.expires_at)
    return {"record_id": generated.record_id, "raw_key": generated.raw_key, "key_preview": generated.key_preview}


@app.post("/api/v1/admin/api-keys/admin/generate")
def admin_generate_admin_api_key(req: AdminApiKeyGenerateReq, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    admin_auth(authorization)
    generated = KEY_STORE.create_admin_api_key(label=req.label, notes=req.notes, is_bootstrap=False)
    if req.expires_at:
        KEY_STORE.update_key_metadata(generated.record_id, expires_at=req.expires_at)
    return {"record_id": generated.record_id, "raw_key": generated.raw_key, "key_preview": generated.key_preview}


@app.get("/api/v1/admin/api-keys")
def admin_list_api_keys(
    authorization: str | None = Header(default=None),
    search: str | None = None,
) -> dict[str, Any]:
    admin_auth(authorization)
    return {"keys": KEY_STORE.load_key_records(key_type="api", key_role=KEY_ROLE_SERVICE, search=search)}


@app.get("/api/v1/admin/api-keys/admin")
def admin_list_admin_api_keys(
    authorization: str | None = Header(default=None),
    search: str | None = None,
) -> dict[str, Any]:
    admin_auth(authorization)
    return {"keys": KEY_STORE.load_key_records(key_type="api", key_role=KEY_ROLE_ADMIN, search=search)}


@app.post("/api/v1/admin/api-keys/revoke")
def admin_revoke_api_key(req: ApiKeyRecordReq, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    admin_auth(authorization)
    if not KEY_STORE.revoke_key(req.record_id):
        raise HTTPException(status_code=404, detail="Key not found")
    return {"ok": True}


@app.post("/api/v1/admin/api-keys/status")
def admin_set_api_key_status(req: ApiKeyStatusReq, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    admin_auth(authorization)
    if not KEY_STORE.toggle_key_status(req.record_id, is_active=req.is_active):
        raise HTTPException(status_code=404, detail="Key not found")
    return {"ok": True}


@app.post("/api/v1/admin/api-keys/update")
def admin_update_api_key(req: ApiKeyUpdateReq, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    admin_auth(authorization)
    updated = KEY_STORE.update_key_metadata(
        req.record_id,
        expires_at=req.expires_at,
        notes=req.notes,
        tier_or_scope=req.tier_or_scope,
        label=req.label,
        max_users=req.max_users,
        trial=req.trial,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Key not found or no changes provided")
    return {"ok": True}
