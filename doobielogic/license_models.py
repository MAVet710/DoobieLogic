from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Literal

PlanType = Literal["trial", "standard", "premium", "enterprise"]
LicenseStatus = Literal["active", "revoked", "expired", "suspended", "disabled"]

ALLOWED_PLAN_TYPES: set[str] = {"trial", "standard", "premium", "enterprise"}
ALLOWED_LICENSE_STATUS: set[str] = {"active", "revoked", "expired", "suspended", "disabled"}


@dataclass
class Customer:
    customer_id: str
    company_name: str
    contact_name: str
    contact_email: str
    created_at: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "Customer":
        return Customer(
            customer_id=str(payload.get("customer_id") or payload.get("id") or "").strip(),
            company_name=str(payload.get("company_name", "")).strip(),
            contact_name=str(payload.get("contact_name") or "").strip(),
            contact_email=str(payload.get("contact_email") or "").strip(),
            created_at=str(payload.get("created_at") or datetime.utcnow().isoformat()),
            notes=str(payload.get("notes") or "").strip(),
        )


@dataclass
class License:
    license_key: str
    customer_id: str
    plan_type: PlanType
    status: LicenseStatus
    issued_at: str
    expires_at: str | None = None
    last_validated_at: str | None = None
    reset_count: int = 0
    revoked_reason: str | None = None
    id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "License":
        return License(
            id=str(payload.get("id")).strip() if payload.get("id") else None,
            license_key=str(payload.get("license_key", "")).strip(),
            customer_id=str(payload.get("customer_id", "")).strip(),
            plan_type=str(payload.get("plan_type", "trial")).strip(),  # type: ignore[arg-type]
            status=str(payload.get("status", "active")).strip(),  # type: ignore[arg-type]
            issued_at=str(payload.get("issued_at") or datetime.utcnow().isoformat()),
            expires_at=str(payload.get("expires_at")).strip() if payload.get("expires_at") else None,
            last_validated_at=str(payload.get("last_validated_at")).strip() if payload.get("last_validated_at") else None,
            reset_count=int(payload.get("reset_count") or 0),
            revoked_reason=str(payload.get("revoked_reason")).strip() if payload.get("revoked_reason") else None,
        )
