from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from doobielogic.config import DoobieConfig, load_doobie_config
from doobielogic.key_management import KEY_ROLE_ADMIN, KEY_TYPE_API, GeneratedKey, KeyStore
from doobielogic.license_models import Customer, License
from doobielogic.license_store import LicenseStore


class AdminGatewayError(RuntimeError):
    pass


class AdminGatewayHttpError(AdminGatewayError):
    def __init__(self, *, status_code: int, path: str, detail: str):
        self.status_code = int(status_code)
        self.path = path
        self.detail = detail
        self.error_category = self._categorize_error(self.status_code)
        super().__init__(f"Admin API request failed ({status_code}) for {path}: {detail}")

    @staticmethod
    def _categorize_error(status_code: int) -> str:
        if status_code == 404:
            return "route_missing"
        if status_code == 401:
            return "unauthorized"
        if status_code == 403:
            return "forbidden"
        if status_code >= 500:
            return "server_error"
        if status_code >= 400:
            return "client_error"
        return "unknown"


class AdminGateway:
    """Unified admin storage gateway.

    Modes:
    - local: read/write local stores (developer mode)
    - remote_api: write/read through Doobie FastAPI admin endpoints (production-safe split deployments)
    """

    def __init__(self, config: DoobieConfig | None = None) -> None:
        self.config = config or load_doobie_config()
        self.remote_base_url = self.config.admin_api_base_url
        self.admin_api_key = self.config.admin_api_key
        self.service_api_key = self.config.api_key
        self.timeout_seconds = self.config.admin_api_timeout

        if self.remote_base_url:
            self.mode = "remote_api"
            self.license_store: LicenseStore | None = None
            self.key_store: KeyStore | None = None
        else:
            self.mode = "local"
            self.license_store = LicenseStore(path=self.config.license_store_path)
            self.key_store = KeyStore(path=self.config.key_store_path)

    def storage_diagnostic(self) -> dict[str, Any]:
        if self.mode == "remote_api":
            return {
                "mode": self.mode,
                "base_url": self.remote_base_url,
                "admin_api_key_configured": bool(self.admin_api_key),
                "service_api_key_configured": bool(self.service_api_key),
                "source_of_truth": "remote_api",
            }
        return {
            "mode": self.mode,
            "license_store": self.config.license_store_path,
            "key_store": self.config.key_store_path,
            "source_of_truth": "local_store",
        }

    def test_connectivity(self) -> dict[str, Any]:
        if self.mode == "local":
            return {"ok": True, "mode": "local", "detail": "Local mode uses direct file/database access."}
        health = self._request("GET", "/health", require_admin_auth=False)
        return {
            "ok": True,
            "mode": self.mode,
            "base_url": self.remote_base_url,
            "remote_health_status": health.get("status"),
            "remote_backend": health.get("backend_mode"),
            "remote_license_store": health.get("license_store"),
            "remote_key_store": health.get("key_store"),
        }

    def admin_diagnostics(self, *, bootstrap_status: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.mode == "local":
            return {
                "mode": "local",
                "admin_api_base_url": None,
                "admin_api_key_configured": bool(self.admin_api_key),
                "service_api_key_configured": bool(self.service_api_key),
                "health": {"status": "local_mode"},
                "bootstrap_routes_available": True,
                "customers_route_available": True,
                "likely_deployment_mismatch": False,
            }

        def _probe(path: str, *, require_admin_auth: bool = True) -> dict[str, Any]:
            try:
                payload = self._request("GET", path, require_admin_auth=require_admin_auth)
                return {"available": True, "status_code": 200, "detail": "ok", "payload_preview": str(payload)[:200]}
            except AdminGatewayHttpError as exc:
                return {
                    "available": False,
                    "status_code": exc.status_code,
                    "path": exc.path,
                    "detail": exc.detail,
                    "error_category": exc.error_category,
                }
            except AdminGatewayError as exc:
                return {"available": False, "status_code": None, "detail": str(exc), "error_category": "network_or_config"}

        health_probe = _probe("/health", require_admin_auth=False)
        bootstrap_probe = bootstrap_status if isinstance(bootstrap_status, dict) and bootstrap_status else _probe(
            "/api/v1/admin/bootstrap/status", require_admin_auth=False
        )
        customers_probe = _probe("/api/v1/admin/customers", require_admin_auth=True)

        bootstrap_available = bool(bootstrap_probe.get("bootstrap_routes_available", bootstrap_probe.get("available", True)))
        customers_available = bool(customers_probe.get("available", True))
        likely_deployment_mismatch = (
            bool(bootstrap_probe.get("backend_compatibility") == "missing_bootstrap_routes")
            or int(customers_probe.get("status_code") or 0) == 404
        )

        return {
            "mode": self.mode,
            "admin_api_base_url": self.remote_base_url,
            "admin_api_key_configured": bool(self.admin_api_key),
            "service_api_key_configured": bool(self.service_api_key),
            "health": health_probe,
            "bootstrap": bootstrap_probe,
            "customers": customers_probe,
            "bootstrap_routes_available": bootstrap_available,
            "customers_route_available": customers_available,
            "likely_deployment_mismatch": likely_deployment_mismatch,
        }

    def _admin_headers(self) -> dict[str, str]:
        if not self.admin_api_key:
            raise AdminGatewayError("ADMIN_API_KEY is required for this operation in remote_api mode.")
        return {"Authorization": f"Bearer {self.admin_api_key}"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        require_admin_auth: bool = True,
    ) -> Any:
        url = f"{self.remote_base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                headers = self._admin_headers() if require_admin_auth else None
                resp = client.request(method, url, headers=headers, json=json_payload)
        except httpx.TimeoutException as exc:
            raise AdminGatewayError(f"Admin API timeout reaching {url}") from exc
        except httpx.HTTPError as exc:
            raise AdminGatewayError(f"Admin API network error reaching {url}: {exc}") from exc

        if resp.status_code >= 400:
            detail = ""
            try:
                body = resp.json()
                detail = str(body.get("detail") or body)
            except Exception:
                detail = resp.text
            raise AdminGatewayHttpError(status_code=resp.status_code, path=path, detail=detail)

        return resp.json()

    # ------- license methods -------
    def list_customers(self) -> list[Customer]:
        if self.mode == "local":
            assert self.license_store is not None
            return self.license_store.list_customers()
        payload = self._request("GET", "/api/v1/admin/customers")
        return [Customer.from_dict(row) for row in payload.get("customers", [])]

    def create_customer(self, company_name: str, contact_name: str, contact_email: str, notes: str = "") -> Customer:
        if self.mode == "local":
            assert self.license_store is not None
            return self.license_store.create_customer(company_name, contact_name, contact_email, notes)
        payload = self._request(
            "POST",
            "/api/v1/admin/customers",
            json_payload={
                "company_name": company_name,
                "contact_name": contact_name,
                "contact_email": contact_email,
                "notes": notes,
            },
        )
        return Customer.from_dict(payload)

    def create_license(self, customer_id: str, plan_type: str, expires_at: str | None = None) -> License:
        if self.mode == "local":
            assert self.license_store is not None
            return self.license_store.create_license(customer_id, plan_type, expires_at=expires_at)
        payload = self._request(
            "POST",
            "/api/v1/admin/licenses/generate",
            json_payload={"customer_id": customer_id, "plan_type": plan_type, "expires_at": expires_at},
        )
        return License.from_dict(payload)

    def list_licenses(self) -> list[License]:
        if self.mode == "local":
            assert self.license_store is not None
            return self.license_store.list_licenses()
        payload = self._request("GET", "/api/v1/admin/licenses")
        return [License.from_dict(row) for row in payload.get("licenses", [])]

    def revoke_license(self, license_key: str, reason: str | None = None) -> License:
        if self.mode == "local":
            assert self.license_store is not None
            return self.license_store.revoke_license(license_key, reason=reason)
        payload = self._request(
            "POST",
            "/api/v1/admin/licenses/revoke",
            json_payload={"license_key": license_key, "revoked_reason": reason},
        )
        return License.from_dict(payload)

    def reset_license(self, license_key: str, reason: str | None = None) -> dict[str, License]:
        if self.mode == "local":
            assert self.license_store is not None
            return self.license_store.reset_license(license_key, reason=reason)
        payload = self._request(
            "POST",
            "/api/v1/admin/licenses/reset",
            json_payload={"license_key": license_key, "reason": reason},
        )
        return {
            "old": License.from_dict(payload["old_license"]),
            "new": License.from_dict(payload["new_license"]),
        }

    def validate_license(self, license_key: str) -> dict[str, Any]:
        if self.mode == "local":
            assert self.license_store is not None
            return self.license_store.validate_license(license_key)
        # Admin-side quick check calls admin validation route to avoid service-key requirement.
        return self._request("POST", "/api/v1/admin/licenses/validate", json_payload={"license_key": license_key})

    # ------- API key methods -------
    def create_api_key(
        self,
        *,
        company_name: str,
        label: str,
        scope: str,
        expiration_date: date | None,
        notes: str,
    ) -> GeneratedKey:
        if self.mode == "local":
            assert self.key_store is not None
            return self.key_store.create_api_key(
                company_name=company_name,
                label=label,
                scope=scope,
                expiration_date=expiration_date,
                notes=notes,
            )
        payload = self._request(
            "POST",
            "/api/v1/admin/api-keys/generate",
            json_payload={
                "company_name": company_name,
                "label": label,
                "scope": scope,
                "expires_at": expiration_date.isoformat() if expiration_date else None,
                "notes": notes,
            },
        )
        return GeneratedKey(record_id=payload["record_id"], raw_key=payload["raw_key"], key_preview=payload["key_preview"])

    def load_api_key_records(self, search: str | None = None) -> list[dict[str, Any]]:
        if self.mode == "local":
            assert self.key_store is not None
            return self.key_store.load_key_records(key_type=KEY_TYPE_API, key_role="service", search=search)
        qs = f"?search={search}" if search else ""
        payload = self._request("GET", f"/api/v1/admin/api-keys{qs}")
        return list(payload.get("keys", []))

    def update_api_key_metadata(self, record_id: str, **kwargs: Any) -> bool:
        if self.mode == "local":
            assert self.key_store is not None
            return self.key_store.update_key_metadata(record_id, **kwargs)
        payload = {"record_id": record_id, **kwargs}
        self._request("POST", "/api/v1/admin/api-keys/update", json_payload=payload)
        return True

    def revoke_api_key(self, record_id: str) -> bool:
        if self.mode == "local":
            assert self.key_store is not None
            return self.key_store.revoke_key(record_id)
        self._request("POST", "/api/v1/admin/api-keys/revoke", json_payload={"record_id": record_id})
        return True

    def toggle_api_key_status(self, record_id: str, is_active: bool) -> bool:
        if self.mode == "local":
            assert self.key_store is not None
            return self.key_store.toggle_key_status(record_id, is_active=is_active)
        self._request(
            "POST",
            "/api/v1/admin/api-keys/status",
            json_payload={"record_id": record_id, "is_active": is_active},
        )
        return True

    def bootstrap_status(self) -> dict[str, Any]:
        if self.mode == "local":
            assert self.key_store is not None
            has_admin_key = self.key_store.has_active_admin_key()
            return {
                "bootstrap_mode": not has_admin_key,
                "admin_api_key_configured": bool(self.admin_api_key),
                "admin_key_source": "key_store" if has_admin_key else "none",
                "bootstrap_routes_available": True,
                "backend_compatibility": "ok",
            }

        try:
            payload = self._request("GET", "/api/v1/admin/bootstrap/status", require_admin_auth=False)
        except AdminGatewayHttpError as exc:
            if exc.status_code == 404:
                return {
                    "bootstrap_mode": None,
                    "admin_api_key_configured": bool(self.admin_api_key),
                    "admin_key_source": "unknown",
                    "bootstrap_routes_available": False,
                    "backend_compatibility": "missing_bootstrap_routes",
                    "compatibility_warning": "Remote API bootstrap routes are not available on the current backend deployment.",
                }
            raise

        payload.setdefault("bootstrap_routes_available", True)
        payload.setdefault("backend_compatibility", "ok")
        return payload

    def bootstrap_generate_initial_admin_key(self, *, label: str, notes: str = "") -> GeneratedKey:
        if self.mode == "local":
            assert self.key_store is not None
            if self.key_store.has_active_admin_key():
                raise AdminGatewayError("Bootstrap unavailable: an admin API key already exists.")
            return self.key_store.create_admin_api_key(label=label, notes=notes, is_bootstrap=True)

        try:
            payload = self._request(
                "POST",
                "/api/v1/admin/bootstrap/generate",
                json_payload={"label": label, "notes": notes},
                require_admin_auth=False,
            )
        except AdminGatewayHttpError as exc:
            if exc.status_code == 404:
                raise AdminGatewayError(
                    "Bootstrap endpoint is unavailable on the remote backend. Deploy a backend that includes "
                    "/api/v1/admin/bootstrap/status and /api/v1/admin/bootstrap/generate."
                ) from exc
            raise

        return GeneratedKey(record_id=payload["record_id"], raw_key=payload["raw_key"], key_preview=payload["key_preview"])

    def create_admin_api_key(
        self,
        *,
        label: str,
        notes: str = "",
        expiration_date: date | None = None,
    ) -> GeneratedKey:
        if self.mode == "local":
            assert self.key_store is not None
            return self.key_store.create_admin_api_key(
                label=label,
                notes=notes,
                expiration_date=expiration_date,
                is_bootstrap=False,
            )
        payload = self._request(
            "POST",
            "/api/v1/admin/api-keys/admin/generate",
            json_payload={
                "label": label,
                "expires_at": expiration_date.isoformat() if expiration_date else None,
                "notes": notes,
            },
        )
        return GeneratedKey(record_id=payload["record_id"], raw_key=payload["raw_key"], key_preview=payload["key_preview"])

    def load_admin_api_key_records(self, search: str | None = None) -> list[dict[str, Any]]:
        if self.mode == "local":
            assert self.key_store is not None
            return self.key_store.load_key_records(key_type=KEY_TYPE_API, key_role=KEY_ROLE_ADMIN, search=search)
        qs = f"?search={search}" if search else ""
        payload = self._request("GET", f"/api/v1/admin/api-keys/admin{qs}")
        return list(payload.get("keys", []))

    def validate_api_key(self, api_key: str) -> dict[str, Any]:
        if self.mode == "local":
            assert self.key_store is not None
            return self.key_store.validate_api_key(api_key)
        return self._request("POST", "/api/v1/keys/validate", json_payload={"api_key": api_key})
