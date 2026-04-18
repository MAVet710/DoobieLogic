from __future__ import annotations

import os

import streamlit as st

from doobielogic.admin_gateway import AdminGateway, AdminGatewayError
from doobielogic.admin_auth import load_admin_auth_config, verify_admin_credentials
from doobielogic.license_models import ALLOWED_PLAN_TYPES
from doobielogic.ui_theme import apply_buyer_dashboard_theme, render_page_hero, section_close, section_open

st.set_page_config(page_title="DoobieLogic Admin Licensing", page_icon="🔐", layout="wide")
apply_buyer_dashboard_theme()
render_page_hero("🔐 DoobieLogic Licensing Admin", "Internal admin operations aligned to the Buyer Dashboard system.")
st.markdown(
    "<span class='dl-pill dl-pill-accent'>Admin Portal</span><span class='dl-pill dl-pill-warning'>Restricted Access</span>",
    unsafe_allow_html=True,
)

if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False


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
        submitted = st.form_submit_button("Unlock Admin Portal")

    if submitted:
        if verify_admin_credentials(username=username, password=provided, config=config):
            st.session_state["admin_authenticated"] = True
            st.success("Authenticated.")
            st.rerun()
        else:
            st.error("Invalid admin credentials.")

    return False


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

section_open()
left, right = st.columns(2)

with left:
    st.subheader("Create Customer")
    with st.form("create_customer"):
        company_name = st.text_input("Company Name")
        contact_name = st.text_input("Contact Name")
        contact_email = st.text_input("Contact Email")
        notes = st.text_area("Notes", value="")
        submitted = st.form_submit_button("Create Customer")
        if submitted:
            if not company_name or not contact_name or not contact_email:
                st.error("Company, contact name, and contact email are required.")
            else:
                customer = gateway.create_customer(company_name, contact_name, contact_email, notes)
                st.success(f"Customer created: {customer.customer_id}")

with right:
    st.subheader("Generate License")
    customers = gateway.list_customers()
    customer_options = {f"{c.company_name} ({c.customer_id})": c.customer_id for c in customers}
    with st.form("generate_license"):
        selected_customer = st.selectbox("Customer", list(customer_options.keys()) if customer_options else ["No customers available"])
        plan_type = st.selectbox("Plan Type", sorted(ALLOWED_PLAN_TYPES))
        expires_at = st.text_input("Expires At (optional ISO8601)", value="")
        generate = st.form_submit_button("Generate License")
        if generate:
            if not customer_options:
                st.error("Create a customer first.")
            else:
                license_obj = gateway.create_license(
                    customer_options[selected_customer],
                    plan_type,
                    expires_at=expires_at.strip() or None,
                )
                st.success(f"License created: {license_obj.license_key}")
section_close()

section_open()
st.subheader("Revoke / Reset License")
with st.form("revoke_reset"):
    license_key = st.text_input("License Key")
    reason = st.text_input("Reason")
    action = st.radio("Action", options=["Revoke", "Reset"], horizontal=True)
    act = st.form_submit_button("Apply")
    if act:
        if not license_key.strip():
            st.error("License key is required.")
        else:
            try:
                if action == "Revoke":
                    revoked = gateway.revoke_license(license_key, reason=reason or None)
                    st.success(f"Revoked {revoked.license_key}")
                else:
                    reset = gateway.reset_license(license_key, reason=reason or None)
                    st.success(f"Reset complete. New key: {reset['new'].license_key}")
            except ValueError as exc:
                st.error(str(exc))
section_close()

section_open()
st.subheader("Customers")
st.dataframe([c.to_dict() for c in gateway.list_customers()], use_container_width=True)
section_close()

section_open()
st.subheader("Licenses")
st.dataframe([l.to_dict() for l in gateway.list_licenses()], use_container_width=True)
section_close()
