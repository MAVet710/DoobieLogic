from __future__ import annotations

import os

import streamlit as st

from doobielogic.admin_auth import logout_admin, require_admin_auth
from doobielogic.license_models import ALLOWED_PLAN_TYPES
from doobielogic.license_store import LicenseStore
from doobielogic.ui_theme import apply_buyer_dashboard_theme, render_page_hero, section_close, section_open

st.set_page_config(page_title="DoobieLogic Admin Licensing", page_icon="🔐", layout="wide")
apply_buyer_dashboard_theme()
render_page_hero("🔐 DoobieLogic Licensing Admin", "Internal admin operations aligned to the Buyer Dashboard system.")
st.markdown(
    "<span class='dl-pill dl-pill-accent'>Admin Portal</span><span class='dl-pill dl-pill-warning'>Restricted Access</span>",
    unsafe_allow_html=True,
)

if not require_admin_auth(form_key="admin_login", submit_label="Unlock Admin Portal"):
    st.stop()

store = LicenseStore(path=os.environ.get("DOOBIE_LICENSE_STORE", "data/license_store.json"))

logout_admin(button_key="admin_logout")

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
                customer = store.create_customer(company_name, contact_name, contact_email, notes)
                st.success(f"Customer created: {customer.customer_id}")

with right:
    st.subheader("Generate License")
    customers = store.list_customers()
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
                license_obj = store.create_license(
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
                    revoked = store.revoke_license(license_key, reason=reason or None)
                    st.success(f"Revoked {revoked.license_key}")
                else:
                    reset = store.reset_license(license_key, reason=reason or None)
                    st.success(f"Reset complete. New key: {reset['new'].license_key}")
            except ValueError as exc:
                st.error(str(exc))
section_close()

section_open()
st.subheader("Customers")
st.dataframe([c.to_dict() for c in store.list_customers()], use_container_width=True)
section_close()

section_open()
st.subheader("Licenses")
st.dataframe([l.to_dict() for l in store.list_licenses()], use_container_width=True)
section_close()
