from __future__ import annotations

import os
from datetime import date
from typing import Any

import streamlit as st

from doobielogic.admin_gateway import AdminGateway, AdminGatewayError
from doobielogic.admin_auth import load_admin_auth_config, verify_admin_credentials
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
        "latest_license_key": None,
        "latest_api_key": None,
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
            st.success("Authenticated.")
            st.rerun()
        else:
            st.error("Invalid admin credentials.")

    return False


_ensure_session_state()

if not _admin_authenticated():
    st.stop()

try:
    gateway = AdminGateway()
except AdminGatewayError as exc:
    st.error(f"Storage/backend configuration error: {exc}")
    st.stop()

st.caption(f"Storage mode: `{gateway.storage_diagnostic().get('mode')}`")

if st.button("Log out", key="admin_logout"):
    st.session_state["admin_authenticated"] = False
    st.rerun()

tab_license, tab_api, tab_manage, tab_validate = st.tabs(
    ["Create License Key", "Service API Keys", "Manage Keys", "Validate Keys"]
)

with tab_license:
    section_open()
    st.subheader("Generate Customer License Key")
    st.caption("Buyer Dashboard customers should use license keys. This is the system of record for customer entitlement.")

    customers = gateway.list_customers()
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
            if not selected_customer:
                st.error("No customer selected. Create a customer first.")
            else:
                customer_id = selected_customer.customer_id
        else:
            if not company_name.strip() or not contact_name.strip() or not contact_email.strip():
                st.error("Company, contact name, and contact email are required to create a new customer.")
            else:
                created_customer = gateway.create_customer(
                    company_name=company_name,
                    contact_name=contact_name,
                    contact_email=contact_email,
                    notes=notes,
                )
                customer_id = created_customer.customer_id

        if customer_id:
            license_obj = gateway.create_license(
                customer_id=customer_id,
                plan_type=plan_type,
                expires_at=expiration_date.isoformat() if has_expiration else None,
            )
            st.session_state["latest_license_key"] = {
                "record_id": license_obj.customer_id,
                "raw_key": license_obj.license_key,
            }
            st.success("License key generated and persisted to license store.")

    _render_latest_generated_key("latest_license_key", kind="License")
    section_close()

with tab_api:
    section_open()
    st.subheader("Generate Service/API Key")
    st.caption(
        "Service API keys are for server-to-server access to DoobieLogic endpoints. "
        "They are not customer license keys."
    )

    with st.form("generate_api_key"):
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
        submitted = st.form_submit_button("Generate API Key")

    if submitted:
        if not company_name.strip() or not label.strip() or not scope.strip():
            st.error("Company, label, and scope are required.")
        else:
            generated = gateway.create_api_key(
                company_name=company_name,
                label=label,
                scope=scope,
                expiration_date=expiration_date if has_expiration else None,
                notes=notes,
            )
            st.session_state["latest_api_key"] = {
                "record_id": generated.record_id,
                "raw_key": generated.raw_key,
            }
            st.success("Service API key generated.")

    _render_latest_generated_key("latest_api_key", kind="Service API Key")
    section_close()

with tab_manage:
    section_open()
    manage_type = st.radio("Select record type", options=["Licenses", "Service API keys"], horizontal=True)

    if manage_type == "Licenses":
        st.subheader("License Inventory")
        licenses = gateway.list_licenses()
        customers = {c.customer_id: c for c in gateway.list_customers()}

        st.dataframe(
            [
                {
                    "license_key": lic.license_key,
                    "customer_id": lic.customer_id,
                    "company": customers.get(lic.customer_id).company_name if customers.get(lic.customer_id) else "Unknown",
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
            selected_license = st.selectbox("Select license", options=[lic.license_key for lic in licenses])
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Revoke license", key=f"revoke_license_{selected_license}"):
                    try:
                        gateway.revoke_license(selected_license, reason="revoked from key management")
                        st.success("License revoked.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
            with col2:
                if st.button("Reset license", key=f"reset_license_{selected_license}"):
                    try:
                        reset_result = gateway.reset_license(selected_license, reason="reset from key management")
                        st.session_state["latest_license_key"] = {
                            "record_id": reset_result["new"].customer_id,
                            "raw_key": reset_result["new"].license_key,
                        }
                        st.success("License reset complete. New license key generated.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
        else:
            st.info("No licenses found. Generate a license first.")

    else:
        st.subheader("Service API Key Inventory")
        search = st.text_input("Search company / label / scope / notes")
        records = gateway.load_api_key_records(search=search or None)

        st.dataframe(
            [
                {
                    "id": r["id"],
                    "company": r["company_name"],
                    "label": r["label"],
                    "scope": r["tier_or_scope"],
                    "created": r["created_at"],
                    "expires": r["expires_at"],
                    "status": "revoked"
                    if int(r["is_revoked"] or 0) == 1
                    else ("active" if int(r["is_active"] or 0) == 1 else "disabled"),
                    "preview": f"...{r['key_preview']}",
                }
                for r in records
            ],
            use_container_width=True,
            hide_index=True,
        )

        if records:
            selectable = {f"{r['id']} | {r['company_name']} | ...{r['key_preview']}": r for r in records}
            selected = st.selectbox("Select key for actions", options=list(selectable.keys()))
            selected_record = selectable[selected]

            with st.form("edit_api_key"):
                new_label = st.text_input("Label", value=selected_record["label"])
                new_scope = st.text_input("Scope", value=selected_record["tier_or_scope"])
                new_expiration = st.text_input("Expires At (ISO8601 or YYYY-MM-DD)", value=selected_record["expires_at"] or "")
                new_notes = st.text_area("Notes", value=selected_record["notes"] or "")
                save_meta = st.form_submit_button("Save metadata")

            if save_meta:
                gateway.update_api_key_metadata(
                    selected_record["id"],
                    label=new_label,
                    tier_or_scope=new_scope,
                    expires_at=new_expiration or None,
                    notes=new_notes,
                )
                st.success("Metadata updated.")
                st.rerun()

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Revoke key", key=f"revoke_api_{selected_record['id']}"):
                    gateway.revoke_api_key(selected_record["id"])
                    st.success("Key revoked.")
                    st.rerun()
            with col2:
                if st.button("Enable key", key=f"enable_api_{selected_record['id']}"):
                    gateway.toggle_api_key_status(selected_record["id"], is_active=True)
                    st.success("Key enabled.")
                    st.rerun()
            with col3:
                if st.button("Disable key", key=f"disable_api_{selected_record['id']}"):
                    gateway.toggle_api_key_status(selected_record["id"], is_active=False)
                    st.success("Key disabled.")
                    st.rerun()
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
            st.session_state["latest_license_validation_result"] = gateway.validate_license(license_key)

    license_result = st.session_state.get("latest_license_validation_result")
    if isinstance(license_result, dict):
        if license_result.get("valid"):
            st.success("License is valid.")
        else:
            st.error(f"Invalid license: {license_result.get('reason', 'unknown')}")
        st.json(license_result)

    st.divider()
    st.subheader("Service API Key Validation")
    with st.form("local_api_validate"):
        api_key = st.text_input("API key to validate", type="password")
        check_api = st.form_submit_button("Validate API key")

    if check_api:
        st.session_state["latest_api_validation_result"] = gateway.validate_api_key(api_key)

    api_result = st.session_state.get("latest_api_validation_result")
    if isinstance(api_result, dict):
        if api_result.get("valid"):
            st.success("API key is valid.")
        else:
            st.error(f"Invalid API key: {api_result.get('reason', 'unknown')}")
        st.json(api_result)

    section_close()
