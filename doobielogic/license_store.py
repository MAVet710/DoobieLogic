from __future__ import annotations

import json
import secrets
import string
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from doobielogic.license_models import ALLOWED_PLAN_TYPES, Customer, License

PLAN_FEATURES: dict[str, dict[str, bool]] = {
    "trial": {
        "buyer_module": True,
        "extraction_module": False,
        "ai_support": True,
        "admin_exports": False,
    },
    "standard": {
        "buyer_module": True,
        "extraction_module": True,
        "ai_support": True,
        "admin_exports": False,
    },
    "premium": {
        "buyer_module": True,
        "extraction_module": True,
        "ai_support": True,
        "admin_exports": True,
    },
    "enterprise": {
        "buyer_module": True,
        "extraction_module": True,
        "ai_support": True,
        "admin_exports": True,
    },
}

_PLAN_PREFIX = {
    "trial": "TRIAL",
    "standard": "STD",
    "premium": "PREM",
    "enterprise": "ENT",
}


class LicenseStore:
    def __init__(self, path: str | Path = "data/license_store.json"):
        self.path = Path(path)
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save({"customers": [], "licenses": []})

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load(self) -> dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("customers", [])
        data.setdefault("licenses", [])
        return data

    def _save(self, payload: dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)

    def diagnostic(self) -> dict[str, str]:
        return {"backend": "local_json", "path": str(self.path)}

    def list_customers(self) -> list[Customer]:
        data = self._load()
        return [Customer.from_dict(row) for row in data.get("customers", [])]

    def list_licenses(self) -> list[License]:
        data = self._load()
        return [License.from_dict(row) for row in data.get("licenses", [])]

    def get_customer(self, customer_id: str) -> Customer | None:
        data = self._load()
        for row in data.get("customers", []):
            if str(row.get("customer_id")) == customer_id:
                return Customer.from_dict(row)
        return None

    def create_customer(
        self,
        company_name: str,
        contact_name: str,
        contact_email: str,
        notes: str = "",
    ) -> Customer:
        customer = Customer(
            customer_id=f"cust_{uuid4().hex[:12]}",
            company_name=company_name.strip(),
            contact_name=contact_name.strip(),
            contact_email=contact_email.strip(),
            created_at=self._now_iso(),
            notes=notes.strip(),
        )
        with self._lock:
            data = self._load()
            data["customers"].append(customer.to_dict())
            self._save(data)
        return customer

    def find_license_by_key(self, license_key: str) -> License | None:
        safe_key = license_key.strip()
        data = self._load()
        for row in data.get("licenses", []):
            if str(row.get("license_key")) == safe_key:
                return License.from_dict(row)
        return None

    def _license_key_exists(self, key: str, data: dict[str, Any]) -> bool:
        for row in data.get("licenses", []):
            if str(row.get("license_key")) == key:
                return True
        return False

    def generate_license_key(self, plan_type: str) -> str:
        safe_plan = plan_type.strip().lower()
        if safe_plan not in ALLOWED_PLAN_TYPES:
            raise ValueError(f"Unsupported plan_type: {plan_type}")

        alphabet = string.ascii_uppercase + string.digits
        prefix = _PLAN_PREFIX[safe_plan]
        return f"DB-{prefix}-{''.join(secrets.choice(alphabet) for _ in range(4))}-{''.join(secrets.choice(alphabet) for _ in range(4))}-{''.join(secrets.choice(alphabet) for _ in range(4))}"

    def create_license(self, customer_id: str, plan_type: str, expires_at: str | None = None) -> License:
        safe_plan = plan_type.strip().lower()
        if safe_plan not in ALLOWED_PLAN_TYPES:
            raise ValueError(f"Unsupported plan_type: {plan_type}")
        if not self.get_customer(customer_id):
            raise ValueError(f"Unknown customer_id: {customer_id}")

        with self._lock:
            data = self._load()
            key = self.generate_license_key(safe_plan)
            while self._license_key_exists(key, data):
                key = self.generate_license_key(safe_plan)

            license_obj = License(
                license_key=key,
                customer_id=customer_id,
                plan_type=safe_plan,
                status="active",
                issued_at=self._now_iso(),
                expires_at=expires_at,
                last_validated_at=None,
                reset_count=0,
                revoked_reason=None,
            )
            data["licenses"].append(license_obj.to_dict())
            self._save(data)
        return license_obj

    def revoke_license(self, license_key: str, reason: str | None = None) -> License:
        safe_key = license_key.strip()
        with self._lock:
            data = self._load()
            for row in data.get("licenses", []):
                if str(row.get("license_key")) != safe_key:
                    continue
                row["status"] = "revoked"
                row["revoked_reason"] = reason.strip() if reason else None
                self._save(data)
                return License.from_dict(row)
        raise ValueError("License not found")

    def reset_license(self, license_key: str, reason: str | None = None) -> dict[str, License]:
        safe_key = license_key.strip()
        with self._lock:
            data = self._load()
            old_row: dict[str, Any] | None = None
            for row in data.get("licenses", []):
                if str(row.get("license_key")) == safe_key:
                    old_row = row
                    break
            if not old_row:
                raise ValueError("License not found")

            old_row["status"] = "revoked"
            old_row["revoked_reason"] = reason.strip() if reason else "reset"
            old_row["last_validated_at"] = old_row.get("last_validated_at")
            next_reset_count = int(old_row.get("reset_count") or 0) + 1

            key = self.generate_license_key(str(old_row.get("plan_type")))
            while self._license_key_exists(key, data):
                key = self.generate_license_key(str(old_row.get("plan_type")))

            new_row = License(
                license_key=key,
                customer_id=str(old_row.get("customer_id")),
                plan_type=str(old_row.get("plan_type")),  # type: ignore[arg-type]
                status="active",
                issued_at=self._now_iso(),
                expires_at=old_row.get("expires_at"),
                last_validated_at=None,
                reset_count=next_reset_count,
                revoked_reason=None,
            )
            data["licenses"].append(new_row.to_dict())
            self._save(data)
        return {"old": License.from_dict(old_row), "new": new_row}

    def validate_license(self, license_key: str) -> dict[str, Any]:
        safe_key = license_key.strip()
        with self._lock:
            data = self._load()
            target: dict[str, Any] | None = None
            for row in data.get("licenses", []):
                if str(row.get("license_key")) == safe_key:
                    target = row
                    break

            if not target:
                return {"valid": False, "reason": "not_found"}

            status = str(target.get("status") or "").lower()
            if status == "revoked":
                return {"valid": False, "reason": "revoked"}
            if status == "suspended":
                return {"valid": False, "reason": "suspended"}

            expires_at = target.get("expires_at")
            if expires_at:
                try:
                    expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                except ValueError:
                    return {"valid": False, "reason": "invalid_expiration_format"}
                if expiry <= datetime.now(timezone.utc):
                    target["status"] = "expired"
                    self._save(data)
                    return {"valid": False, "reason": "expired"}

            if status != "active":
                return {"valid": False, "reason": status or "not_found"}

            target["last_validated_at"] = self._now_iso()
            self._save(data)

            customer = self.get_customer(str(target.get("customer_id")))
            company_name = customer.company_name if customer else "Unknown"
            plan_type = str(target.get("plan_type"))

            return {
                "valid": True,
                "customer_id": str(target.get("customer_id")),
                "company_name": company_name,
                "plan_type": plan_type,
                "status": "active",
                "expires_at": target.get("expires_at"),
                "features": PLAN_FEATURES.get(plan_type, {}),
                "diagnostic": self.diagnostic(),
            }
