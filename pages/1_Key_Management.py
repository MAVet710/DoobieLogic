from __future__ import annotations

import os
from datetime import date
from typing import Any, Callable

import streamlit as st

from doobielogic.admin_gateway import AdminGateway, AdminGatewayError, AdminGatewayHttpError
from doobielogic.admin_auth import load_admin_auth_config, verify_admin_credentials
from doobielogic.config import load_doobie_config, resolve_doobie_config_source
from doobielogic.license_models import ALLOWED_PLAN_TYPES
from doobielogic.ui_theme import apply_buyer_dashboard_theme, render_page_hero, section_close, section_open

st.set_page_config(page_title="Key Management", page_icon="🗝️", layout="wide")
apply_buyer_dashboard_theme()
render_page_hero(
    "🗝️ Key Management",
    "Admin-only key generation and lifecycle controls. Customer access is license-based; service integrations use API keys.",
)
st.markdown(
    "<span class='dl-pill dl-pill-accent'>Security Console</span><span class='dl-pill dl-pill-warning'>Admin Only</span>",
    unsafe_allow_html=True,
)


def _ensure_session_state() -> None:
    defaults: dict[str, Any] = {
        "admin_authenticated": False,
        "admin_username": None,
        "admin_password": None,
        "active_admin_api_key": None,
        "latest_license_key": None,
        "latest_service_api_key": None,
        "latest_admin_api_key": None,
        "latest_license_validation_result": None,
        "latest_api_validation_result": None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _render_latest_generated_key(session_key: str, *, kind: str) -> None:
    payload = st.session_state.get(session_key)
    if not isinstance(payload, dict):
        return

    raw_key = payload.get("raw_key")
    if not isinstance(raw_key, str) or not raw_key.strip():
        return

    record_id = payload.get("record_id")
    safe_kind = kind.strip() or "Key"
    filename_kind = safe_kind.lower().replace(" ", "_")
    filename = f"doobielogic_{filename_kind}.txt"

    st.success(f"New {safe_kind} generated. Copy and store it now—this raw value is shown once.")
    st.code(raw_key, language="text")
    if record_id:
        st.caption(f"Record ID: {record_id}")

    st.download_button(
        label=f"Download {safe_kind}",
        data=f"{raw_key}\n",
        file_name=filename,
        mime="text/plain",
        key=f"download_{session_key}",
    )


def _mask_key(raw_key: str) -> str:
    safe = (raw_key or "").strip()
    if len(safe) <= 12:
        return "*" * len(safe)
    return f"{safe[:8]}...{safe[-4:]}"


def _admin_authenticated() -> bool:
    config = load_admin_auth_config(st.secrets if hasattr(st, "secrets") else None, os.environ)

    if not config.password_hash:
        st.error("Admin authentication is not configured: password hash secret is missing.")
        return False

    if st.session_state.get("admin_authenticated"):
        return True

    with st.form("admin_login"):
        username = ""
        if config.username:
            username = st.text_input("Admin username")
        provided = st.text_input("Admin password", type="password")
        submitted = st.form_submit_button("Unlock Key Management")

    if submitted:
        if verify_admin_credentials(username=username, password=provided, config=config):
            st.session_state["admin_authenticated"] = True
            st.session_state["admin_username"] = username or config.username
            st.session_state["admin_password"] = provided
            st.success("Authenticated.")
            st.rerun()
        else:
            st.error("Invalid admin credentials.")

    return False


def _status_tag(record: dict[str, Any]) -> str:
    if int(record.get("is_revoked") or 0) == 1:
        return "revoked"
    if int(record.get("is_active") or 0) != 1:
        return "disabled"
    if record.get("expires_at"):
        return "active/expiring"
    return "active"


def _render_admin_error(section: str, exc: Exception) -> None:
    if isinstance(exc, AdminGatewayHttpError):
        st.warning(
            f"{section}: admin API request failed.\n"
            f"Route: `{exc.path}`\n"
            f"Status: `{exc.status_code}` ({exc.error_category})\n"
            f"Detail: `{exc.detail or 'n/a'}`"
        )
        hints = {
            "route_missing": "Route exists in this repo but may be missing from the live deployment. Backend may be older than this UI deployment.",
            "unauthorized": "Admin API key may be invalid or missing in the active configuration.",
            "forbidden": "Admin credentials are valid but do not have permission for this endpoint.",
            "server_error": "Backend threw an internal error. Check API logs for stack traces and storage/config issues.",
            "client_error": "Request was rejected by backend. Verify request payload and backend expectations.",
            "unknown": "Unexpected API failure. Verify deployment health and network connectivity.",
        }
        st.caption(f"Hint: {hints.get(exc.error_category, hints['unknown'])}")
    else:
        st.warning(f"{section}: {exc}")


def _safe_gateway_call(section: str, fn: Callable[[], Any], *, fallback: Any) -> tuple[Any, Exception | None]:
    try:
        return fn(), None
    except (AdminGatewayError, ValueError) as exc:
        _render_admin_error(section, exc)
        return fallback, exc


_ensure_session_state()
runtime_config_source = resolve_doobie_config_source(secrets=st.secrets if hasattr(st, "secrets") else None, env=os.environ)

if not _admin_authenticated():
    st.stop()

try:
    gateway = AdminGateway(config=load_doobie_config(runtime_config_source))
except AdminGatewayError as exc:
    st.error(f"Storage/backend configuration error: {exc}")
    st.stop()

config = load_doobie_config(runtime_config_source)
diagnostic = gateway.storage_diagnostic()
mode = diagnostic.get("mode")

if mode == "remote_api":
    env_admin_key_configured = bool(config.admin_api_key)
    if not env_admin_key_configured and st.session_state.get("active_admin_api_key"):
        gateway.set_admin_api_key(st.session_state["active_admin_api_key"])
    gateway.set_admin_basic_credentials(
        st.session_state.get("admin_username"),
        st.session_state.get("admin_password"),
    )

bootstrap, bootstrap_error = _safe_gateway_call("Bootstrap status", gateway.bootstrap_status, fallback={})
bootstrap_routes_available = bool(bootstrap.get("bootstrap_routes_available", True))
bootstrap_mode = bootstrap.get("bootstrap_mode")
backend_compatibility = str(bootstrap.get("backend_compatibility") or "unknown")
has_effective_admin_key = (mode != "remote_api") or gateway.has_admin_api_key()

diagnostics_snapshot = gateway.admin_diagnostics(bootstrap_status=bootstrap if isinstance(bootstrap, dict) else None)

if mode == "remote_api":
    st.info(f"Backend mode: **REMOTE API** (`{diagnostic.get('base_url')}`)")
else:
    st.success("Backend mode: **LOCAL** (file/db direct access)")

st.markdown("### Admin console status")
if st.session_state.get("admin_authenticated"):
    st.success("God login status: **Authenticated**")
else:
    st.error("God login status: **Locked**")

if bootstrap_mode is True:
    st.warning("Bootstrap status: **Needs initial persistent admin API key**")
elif bootstrap_mode is False:
    st.success("Bootstrap status: **Complete**")
else:
    st.info("Bootstrap status: **Unknown**")

if mode == "remote_api":
    st.markdown("#### Active admin API key (for remote admin routes)")
    if config.admin_api_key:
        st.caption("Using ADMIN_API_KEY from secrets/env (compatibility mode).")
        st.code(_mask_key(config.admin_api_key), language="text")
    else:
        with st.form("set_runtime_admin_api_key"):
            runtime_admin_key = st.text_input(
                "Paste a persistent admin API key",
                type="password",
                help="Used only for this Streamlit session; not persisted to secrets/env.",
            )
            set_runtime_admin_key = st.form_submit_button("Use Admin API Key for This Session")
        if set_runtime_admin_key:
            if runtime_admin_key.strip():
                st.session_state["active_admin_api_key"] = runtime_admin_key.strip()
                gateway.set_admin_api_key(runtime_admin_key.strip())
                st.success("Session admin API key applied.")
                st.rerun()
            else:
                st.error("Provide an admin API key to continue.")
        active_runtime_key = st.session_state.get("active_admin_api_key")
        if active_runtime_key:
            st.caption("Session key loaded")
            st.code(_mask_key(active_runtime_key), language="text")
            if st.button("Clear session admin API key", key="clear_runtime_admin_key"):
                st.session_state["active_admin_api_key"] = None
                st.rerun()
        elif bootstrap_mode is False:
            st.warning("Bootstrap is complete, but no active admin API key is loaded for this session.")

if bootstrap_error:
    st.info("Bootstrap status is currently unavailable. Other admin sections will still render when possible.")
elif not bootstrap_routes_available:
    st.warning(
        "Remote API bootstrap routes are not available on the current backend deployment. "
        "The page will continue to load, but initial bootstrap key generation requires a backend redeploy."
    )
elif bootstrap_mode is True:
    st.warning("No persistent admin API key exists yet. Bootstrap mode is active for initial admin-key creation.")
elif bootstrap_mode is False:
    st.success(f"Admin API key source: **{bootstrap.get('admin_key_source', 'unknown')}**")
else:
    st.info("Bootstrap status is unavailable. Verify backend compatibility and connectivity.")

if diagnostics_snapshot.get("likely_deployment_mismatch"):
    st.warning("Live API may be running an older build than this UI. Expected admin routes returned 404.")

if config.diagnostics()["warnings"]:
    st.warning("Configuration warnings: " + ", ".join(config.diagnostics()["warnings"]))

with st.expander("Backend / storage diagnostics", expanded=False):
    st.json(
        {
            "config": config.diagnostics(),
            "gateway": diagnostic,
            "bootstrap": bootstrap,
            "admin_api_diagnostics": diagnostics_snapshot,
            "ui_diagnostics": {
                "mode": mode,
                "bootstrap_routes_available": bootstrap_routes_available,
                "persistent_admin_key_exists": (bootstrap_mode is False) if bootstrap_mode is not None else None,
                "bootstrap_mode": bootstrap_mode,
                "backend_compatibility": backend_compatibility,
            },
        }
    )
    if st.button("Test connectivity", key="test_connectivity"):
        probe, _ = _safe_gateway_call("Connectivity test", gateway.test_connectivity, fallback={"ok": False})
        st.json(probe)

if st.button("Log out", key="admin_logout"):
    st.session_state["admin_authenticated"] = False
    st.session_state["admin_username"] = None
    st.session_state["admin_password"] = None
    st.session_state["active_admin_api_key"] = None
    st.rerun()

tab_license, tab_api, tab_manage, tab_validate = st.tabs(
    ["Customer License Keys", "Admin + Service API Keys", "Manage Keys", "Validate Keys"]
)

with tab_license:
    section_open()
    st.subheader("Generate Customer License Key")
    st.caption("Customer license keys are used by Buyer Dashboard customers for entitlement and plan validation.")

    if mode == "remote_api" and not has_effective_admin_key:
        st.warning("Load an admin API key above to create/list customers and issue licenses in remote mode.")
        customers, customers_error = [], None
    else:
        customers, customers_error = _safe_gateway_call("Load customers", gateway.list_customers, fallback=[])
    customer_lookup = {f"{c.company_name} ({c.customer_id})": c for c in customers}
    customer_mode_options = ["Use existing customer", "Create new customer"]

    with st.form("generate_license_key"):
        mode = st.radio("Customer mode", options=customer_mode_options, horizontal=True)

        if mode == "Use existing customer":
            selected_customer_label = st.selectbox(
                "Customer",
                options=list(customer_lookup.keys()) if customer_lookup else ["No customers available"],
            )
            contact_name = ""
            contact_email = ""
            company_name = ""
        else:
            company_name = st.text_input("Company / Customer Name")
            contact_name = st.text_input("Primary Contact Name")
            contact_email = st.text_input("Primary Contact Email")
            selected_customer_label = ""

        plan_type = st.selectbox("Plan", options=sorted(ALLOWED_PLAN_TYPES))
        has_expiration = st.checkbox("Set expiration date", value=False)
        expiration_date = st.date_input("Expiration date", value=date.today(), disabled=not has_expiration)
        notes = st.text_area("Customer notes")
        submitted = st.form_submit_button("Generate License Key")

    if submitted:
        customer_id: str | None = None
        if mode == "Use existing customer":
            selected_customer = customer_lookup.get(selected_customer_label)
            if customers_error:
                st.error("Unable to load existing customers. Use 'Create new customer' or fix admin API access.")
            elif not selected_customer:
                st.error("No customer selected. Create a customer first.")
            else:
                customer_id = selected_customer.customer_id
        else:
            if not company_name.strip() or not contact_name.strip() or not contact_email.strip():
                st.error("Company, contact name, and contact email are required to create a new customer.")
            else:
                created_customer, create_customer_error = _safe_gateway_call(
                    "Create customer",
                    lambda: gateway.create_customer(
                        company_name=company_name,
                        contact_name=contact_name,
                        contact_email=contact_email,
                        notes=notes,
                    ),
                    fallback=None,
                )
                if create_customer_error:
                    st.error("Could not create customer. License generation aborted.")
                elif created_customer:
                    customer_id = created_customer.customer_id

        if customer_id:
            try:
                license_obj = gateway.create_license(
                    customer_id=customer_id,
                    plan_type=plan_type,
                    expires_at=expiration_date.isoformat() if has_expiration else None,
                )
                st.session_state["latest_license_key"] = {
                    "record_id": license_obj.customer_id,
                    "raw_key": license_obj.license_key,
                }
                st.success("License key generated and persisted to the active source of truth.")
            except (ValueError, AdminGatewayError) as exc:
                _render_admin_error("License creation failed", exc)

    _render_latest_generated_key("latest_license_key", kind="Customer License Key")
    section_close()

with tab_api:
    section_open()
    st.subheader("Admin + Service API Key Generation")
    st.caption(
        "Admin API keys authenticate internal admin automation. Service API keys authenticate server-to-server product integrations."
    )

    if bootstrap_routes_available and bootstrap_mode is True:
        st.info("Bootstrap is active: generate the initial persistent admin API key here.")
        with st.form("bootstrap_admin_key"):
            label = st.text_input("Bootstrap key label", value="Initial Bootstrap Admin Key")
            notes = st.text_area("Bootstrap notes", value="Created from Streamlit admin bootstrap flow")
            bootstrap_create = st.form_submit_button("Generate Initial Admin API Key")
        if bootstrap_create:
            try:
                generated = gateway.bootstrap_generate_initial_admin_key(label=label, notes=notes)
                gateway.set_admin_api_key(generated.raw_key)
                st.session_state["active_admin_api_key"] = generated.raw_key
                st.session_state["latest_admin_api_key"] = {"record_id": generated.record_id, "raw_key": generated.raw_key}
                st.success("Initial admin API key created and persisted.")
                st.rerun()
            except AdminGatewayError as exc:
                _render_admin_error("Bootstrap failed", exc)

    if mode == "remote_api" and not bootstrap_routes_available:
        st.warning("Initial admin-key bootstrap is blocked: backend is missing bootstrap endpoints.")
        st.markdown(
            "**Next step:** Redeploy the FastAPI backend from this repository version so it includes\n"
            "`GET /api/v1/admin/bootstrap/status` and `POST /api/v1/admin/bootstrap/generate`.\n\n"
            "After redeploy, refresh this page and use **Generate Initial Admin API Key**."
        )

    st.markdown("#### Generate additional admin API key")
    with st.form("generate_admin_api_key"):
        admin_label = st.text_input("Admin key label", value="Admin automation key")
        admin_has_expiration = st.checkbox("Set expiration date", value=False, key="admin_api_has_expiration")
        admin_expiration_date = st.date_input(
            "Expiration date",
            value=date.today(),
            disabled=not admin_has_expiration,
            key="admin_api_expiration",
        )
        admin_notes = st.text_area("Notes", key="admin_api_notes")
        admin_submitted = st.form_submit_button("Generate Admin API Key")

    if admin_submitted:
        if mode == "remote_api" and not has_effective_admin_key:
            st.error("Load an admin API key above before generating additional admin keys.")
        elif not admin_label.strip():
            st.error("Admin key label is required.")
        else:
            try:
                generated = gateway.create_admin_api_key(
                    label=admin_label,
                    expiration_date=admin_expiration_date if admin_has_expiration else None,
                    notes=admin_notes,
                )
                st.session_state["latest_admin_api_key"] = {
                    "record_id": generated.record_id,
                    "raw_key": generated.raw_key,
                }
                st.success("Admin API key generated in the active backend.")
            except (ValueError, AdminGatewayError) as exc:
                _render_admin_error("Admin API key creation failed", exc)

    _render_latest_generated_key("latest_admin_api_key", kind="Admin API Key")

    st.divider()
    st.markdown("#### Generate service API key")
    with st.form("generate_service_api_key"):
        company_name = st.text_input("Company Name", key="api_company")
        label = st.text_input("Key label", key="api_label")
        scope = st.text_input("Access scope (comma separated)", value="buyer_dashboard", key="api_scope")
        has_expiration = st.checkbox("Set expiration date", value=False, key="api_has_expiration")
        expiration_date = st.date_input(
            "Expiration date",
            value=date.today(),
            disabled=not has_expiration,
            key="api_expiration",
        )
        notes = st.text_area("Notes", key="api_notes")
        submitted = st.form_submit_button("Generate Service API Key")

    if submitted:
        if mode == "remote_api" and not has_effective_admin_key:
            st.error("Load an admin API key above before generating service keys.")
        elif not company_name.strip() or not label.strip() or not scope.strip():
            st.error("Company, label, and scope are required.")
        else:
            try:
                generated = gateway.create_api_key(
                    company_name=company_name,
                    label=label,
                    scope=scope,
                    expiration_date=expiration_date if has_expiration else None,
                    notes=notes,
                )
                st.session_state["latest_service_api_key"] = {
                    "record_id": generated.record_id,
                    "raw_key": generated.raw_key,
                }
                st.success("Service API key generated in the active backend.")
            except (ValueError, AdminGatewayError) as exc:
                _render_admin_error("Service API key creation failed", exc)

    _render_latest_generated_key("latest_service_api_key", kind="Service API Key")
    section_close()

with tab_manage:
    section_open()
    manage_type = st.radio("Select record type", options=["Licenses", "API keys"], horizontal=True)

    if manage_type == "Licenses":
        st.subheader("Customer License Inventory")
        if mode == "remote_api" and not has_effective_admin_key:
            st.warning("Load an admin API key above to manage licenses in remote mode.")
            licenses, licenses_error = [], None
            customers, customer_error = [], None
        else:
            licenses, licenses_error = _safe_gateway_call("Load licenses", gateway.list_licenses, fallback=[])
            customers, customer_error = _safe_gateway_call("Load customers", gateway.list_customers, fallback=[])
        customers_by_id = {c.customer_id: c for c in customers}

        if licenses_error and customer_error:
            st.info("License management is temporarily unavailable because required admin routes failed.")
        else:
            st.dataframe(
                [
                    {
                        "license_key": lic.license_key,
                        "customer_id": lic.customer_id,
                        "company": customers_by_id.get(lic.customer_id).company_name if customers_by_id.get(lic.customer_id) else "Unknown",
                        "plan": lic.plan_type,
                        "status": lic.status,
                        "issued_at": lic.issued_at,
                        "expires_at": lic.expires_at,
                        "last_validated_at": lic.last_validated_at,
                        "reset_count": lic.reset_count,
                        "revoked_reason": lic.revoked_reason,
                    }
                    for lic in licenses
                ],
                use_container_width=True,
                hide_index=True,
            )

            if licenses:
                license_options = {
                    f"{lic.license_key} · {customers_by_id.get(lic.customer_id).company_name if customers_by_id.get(lic.customer_id) else 'Unknown'}": (
                        lic.id or lic.license_key
                    )
                    for lic in licenses
                }
                selected_label = st.selectbox("Select license", options=list(license_options.keys()))
                selected_license = license_options[selected_label]
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Revoke license", key=f"revoke_license_{selected_label}"):
                        try:
                            gateway.revoke_license(selected_license, reason="revoked from key management")
                            st.success("License revoked.")
                            st.rerun()
                        except (ValueError, AdminGatewayError) as exc:
                            _render_admin_error("Revoke license failed", exc)
                with col2:
                    if st.button("Reset license", key=f"reset_license_{selected_label}"):
                        try:
                            reset_result = gateway.reset_license(selected_license, reason="reset from key management")
                            st.session_state["latest_license_key"] = {
                                "record_id": reset_result["new"].customer_id,
                                "raw_key": reset_result["new"].license_key,
                            }
                            st.success("License reset complete. New license key generated.")
                            st.rerun()
                        except (ValueError, AdminGatewayError) as exc:
                            _render_admin_error("Reset license failed", exc)
            else:
                st.info("No licenses found. Generate a license first.")

    else:
        st.subheader("API Key Inventory (Persistent)")
        search = st.text_input("Search company / label / scope / notes")
        if mode == "remote_api" and not has_effective_admin_key:
            st.warning("Load an admin API key above to manage API key records in remote mode.")
            service_records, service_error = [], None
            admin_records, admin_error = [], None
        else:
            service_records, service_error = _safe_gateway_call(
                "Load service API keys",
                lambda: gateway.load_api_key_records(search=search or None),
                fallback=[],
            )
            admin_records, admin_error = _safe_gateway_call(
                "Load admin API keys",
                lambda: gateway.load_admin_api_key_records(search=search or None),
                fallback=[],
            )
        records = admin_records + service_records

        if service_error and admin_error:
            st.info("API key inventory is temporarily unavailable because admin routes failed.")
        else:
            st.dataframe(
                [
                    {
                        "id": r["id"],
                        "key_type": "admin" if r.get("key_role") == "admin" else "service",
                        "bootstrap": "yes" if int(r.get("is_bootstrap") or 0) == 1 else "no",
                        "company": r["company_name"],
                        "label": r["label"],
                        "scope": r["tier_or_scope"],
                        "created_at": r["created_at"],
                        "expires_at": r["expires_at"],
                        "status": _status_tag(r),
                        "preview": f"...{r['key_preview']}",
                    }
                    for r in records
                ],
                use_container_width=True,
                hide_index=True,
            )

            if records:
                selectable = {f"{r['id']} | {r['label']} | ...{r['key_preview']}": r for r in records}
                selected = st.selectbox("Select key for actions", options=list(selectable.keys()))
                selected_record = selectable[selected]

                with st.form("edit_api_key"):
                    new_label = st.text_input("Label", value=selected_record["label"])
                    new_scope = st.text_input("Scope", value=selected_record["tier_or_scope"])
                    new_expiration = st.text_input("Expires At (ISO8601 or YYYY-MM-DD)", value=selected_record["expires_at"] or "")
                    new_notes = st.text_area("Notes", value=selected_record["notes"] or "")
                    save_meta = st.form_submit_button("Save metadata")

                if save_meta:
                    try:
                        gateway.update_api_key_metadata(
                            selected_record["id"],
                            label=new_label,
                            tier_or_scope=new_scope,
                            expires_at=new_expiration or None,
                            notes=new_notes,
                        )
                        st.success("Metadata updated.")
                        st.rerun()
                    except (ValueError, AdminGatewayError) as exc:
                        _render_admin_error("Failed to update metadata", exc)

                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Revoke key", key=f"revoke_api_{selected_record['id']}"):
                        try:
                            gateway.revoke_api_key(selected_record["id"])
                            st.success("Key revoked.")
                            st.rerun()
                        except (ValueError, AdminGatewayError) as exc:
                            _render_admin_error("Failed to revoke key", exc)
                with col2:
                    if st.button("Enable key", key=f"enable_api_{selected_record['id']}"):
                        try:
                            gateway.toggle_api_key_status(selected_record["id"], is_active=True)
                            st.success("Key enabled.")
                            st.rerun()
                        except (ValueError, AdminGatewayError) as exc:
                            _render_admin_error("Failed to enable key", exc)
                with col3:
                    if st.button("Disable key", key=f"disable_api_{selected_record['id']}"):
                        try:
                            gateway.toggle_api_key_status(selected_record["id"], is_active=False)
                            st.success("Key disabled.")
                            st.rerun()
                        except (ValueError, AdminGatewayError) as exc:
                            _render_admin_error("Failed to disable key", exc)
            else:
                st.info("No API keys found. Generate an API key first.")

    section_close()

with tab_validate:
    section_open()
    st.subheader("License Validation (Buyer Dashboard flow)")
    st.caption(
        "Primary flow: Buyer Dashboard sends a customer license key to DoobieLogic, authenticated with a service API key."
    )

    with st.form("local_license_validate"):
        license_key = st.text_input("License key to validate", type="password")
        check_license = st.form_submit_button("Validate license")

    if check_license:
        if not license_key.strip():
            st.session_state["latest_license_validation_result"] = {
                "valid": False,
                "reason": "missing_key",
            }
        else:
            try:
                st.session_state["latest_license_validation_result"] = gateway.validate_license(license_key)
            except AdminGatewayError as exc:
                st.session_state["latest_license_validation_result"] = {"valid": False, "reason": "backend_unavailable", "detail": str(exc)}

    license_result = st.session_state.get("latest_license_validation_result")
    if isinstance(license_result, dict):
        if license_result.get("valid"):
            st.success("License is valid.")
        else:
            reason = str(license_result.get("reason", "unknown"))
            detail = str(license_result.get("detail") or "")
            st.error(f"Invalid license: {reason}" + (f" ({detail})" if detail else ""))
        st.json(license_result)

    st.divider()
    st.subheader("Service API Key Validation")
    with st.form("local_api_validate"):
        api_key = st.text_input("API key to validate", type="password")
        check_api = st.form_submit_button("Validate API key")

    if check_api:
        try:
            st.session_state["latest_api_validation_result"] = gateway.validate_api_key(api_key)
        except AdminGatewayError as exc:
            st.session_state["latest_api_validation_result"] = {"valid": False, "reason": "backend_unavailable", "detail": str(exc)}

    api_result = st.session_state.get("latest_api_validation_result")
    if isinstance(api_result, dict):
        if api_result.get("valid"):
            st.success("API key is valid.")
        else:
            reason = str(api_result.get("reason", "unknown"))
            detail = str(api_result.get("detail") or "")
            st.error(f"Invalid API key: {reason}" + (f" ({detail})" if detail else ""))
        st.json(api_result)

    section_close()
