from __future__ import annotations

import os
from datetime import date

import streamlit as st

from doobielogic.admin_auth import verify_admin_password
from doobielogic.key_management import KEY_TYPE_API, KEY_TYPE_LICENSE, KeyStore

st.set_page_config(page_title="Key Management", page_icon="🗝️", layout="wide")
st.title("🗝️ Key Management")
st.caption("Admin-only key generation and lifecycle controls for license and API access.")


def _admin_authenticated() -> bool:
    if st.session_state.get("admin_authenticated"):
        return True

    admins = {}
    if hasattr(st, "secrets"):
        auth_block = st.secrets.get("auth", {})
        if isinstance(auth_block, dict):
            maybe_admins = auth_block.get("admins", {})
            if isinstance(maybe_admins, dict):
                admins = {str(k): str(v) for k, v in maybe_admins.items()}

    env_user = os.environ.get("DOOBIE_ADMIN_USERNAME")
    env_password = os.environ.get("DOOBIE_ADMIN_PASSWORD")
    if env_user and env_password:
        admins.setdefault(env_user, env_password)

    if not admins:
        st.error(
            "No admin credentials configured. Set Streamlit secret [auth.admins] or DOOBIE_ADMIN_USERNAME/DOOBIE_ADMIN_PASSWORD."
        )
        return False

    with st.form("admin_login"):
        username = st.text_input("Admin username")
        provided = st.text_input("Admin password", type="password")
        submitted = st.form_submit_button("Unlock Key Management")
    if submitted:
        if verify_admin_password(username, provided, admins):
            st.session_state.admin_authenticated = True
            st.session_state.admin_username = username
            st.success("Authenticated.")
            st.rerun()
        else:
            st.error("Invalid admin password.")
    return False


if not _admin_authenticated():
    st.stop()

store = KeyStore(path=os.environ.get("DOOBIE_KEY_DB", "data/key_store.db"))
if st.session_state.get("admin_username"):
    st.caption(f"Signed in as: {st.session_state.admin_username}")
if st.button("Log out", key="admin_logout"):
    st.session_state.admin_authenticated = False
    st.session_state.admin_username = ""
    st.rerun()

tab_license, tab_api, tab_manage, tab_validate = st.tabs(
    ["License Keys", "API Keys", "Manage Keys", "Validation Tester"]
)

with tab_license:
    st.subheader("Generate License Key")
    with st.form("generate_license_key"):
        company_name = st.text_input("Company / Customer Name")
        contact_email = st.text_input("Email (optional)")
        tier = st.selectbox("Tier / Plan", ["trial", "standard", "premium", "enterprise"])
        expiration = st.date_input("Expiration date (optional)", value=None)
        max_users = st.number_input("Max users (optional)", min_value=1, value=1)
        trial = st.checkbox("Trial license", value=False)
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Generate License Key")
        if submitted:
            if not company_name.strip():
                st.error("Company name is required.")
            else:
                generated = store.create_license_key(
                    company_name=company_name,
                    email=contact_email or None,
                    tier=tier,
                    expiration_date=expiration if isinstance(expiration, date) else None,
                    max_users=max_users,
                    trial=trial,
                    notes=notes,
                )
                st.success("License key created. This is the only time the raw key is shown.")
                st.code(generated.raw_key)
                st.download_button(
                    "Download License Key",
                    data=f"{generated.raw_key}\n",
                    file_name=f"license_key_{generated.record_id}.txt",
                    mime="text/plain",
                )

with tab_api:
    st.subheader("Generate API Key")
    with st.form("generate_api_key"):
        company_name = st.text_input("Company Name", key="api_company")
        label = st.text_input("Key label", key="api_label")
        scope = st.text_input("Access scope (comma separated)", value="buyer_dashboard", key="api_scope")
        expiration = st.date_input("Expiration date (optional)", value=None, key="api_expiration")
        notes = st.text_area("Notes", key="api_notes")
        submitted = st.form_submit_button("Generate API Key")
        if submitted:
            if not company_name.strip() or not label.strip() or not scope.strip():
                st.error("Company, label, and scope are required.")
            else:
                generated = store.create_api_key(
                    company_name=company_name,
                    label=label,
                    scope=scope,
                    expiration_date=expiration if isinstance(expiration, date) else None,
                    notes=notes,
                )
                st.success("API key created. This is the only time the raw key is shown.")
                st.code(generated.raw_key)
                st.download_button(
                    "Download API Key",
                    data=f"{generated.raw_key}\n",
                    file_name=f"api_key_{generated.record_id}.txt",
                    mime="text/plain",
                )

with tab_manage:
    st.subheader("Key Inventory")
    filter_type = st.selectbox("Filter by key type", options=["all", KEY_TYPE_LICENSE, KEY_TYPE_API])
    search = st.text_input("Search company / label / scope / notes")
    chosen_type = None if filter_type == "all" else filter_type
    records = store.load_key_records(key_type=chosen_type, search=search or None)
    st.dataframe(
        [
            {
                "id": r["id"],
                "type": r["key_type"],
                "company": r["company_name"],
                "label": r["label"],
                "tier_or_scope": r["tier_or_scope"],
                "created": r["created_at"],
                "expires": r["expires_at"],
                "status": "revoked"
                if int(r["is_revoked"] or 0) == 1
                else ("active" if int(r["is_active"] or 0) == 1 else "disabled"),
                "preview": f"...{r['key_preview']}",
                "trial": bool(r["trial"]),
                "max_users": r["max_users"],
            }
            for r in records
        ],
        use_container_width=True,
        hide_index=True,
    )
    if records:
        selectable = {f"{r['id']} | {r['key_type']} | {r['company_name']} | ...{r['key_preview']}": r for r in records}
        selected = st.selectbox("Select key for actions", options=list(selectable.keys()))
        selected_record = selectable[selected]
        with st.form("edit_key"):
            new_label = st.text_input("Label", value=selected_record["label"])
            new_scope = st.text_input("Tier / Scope", value=selected_record["tier_or_scope"])
            new_expiration = st.text_input("Expires At (ISO8601 or YYYY-MM-DD)", value=selected_record["expires_at"] or "")
            new_notes = st.text_area("Notes", value=selected_record["notes"] or "")
            new_max_users = st.number_input(
                "Max users",
                min_value=1,
                value=int(selected_record["max_users"] or 1),
                disabled=selected_record["key_type"] != KEY_TYPE_LICENSE,
            )
            new_trial = st.checkbox("Trial", value=bool(selected_record["trial"]), disabled=selected_record["key_type"] != KEY_TYPE_LICENSE)
            save_meta = st.form_submit_button("Save metadata")
            if save_meta:
                store.update_key_metadata(
                    selected_record["id"],
                    label=new_label,
                    tier_or_scope=new_scope,
                    expires_at=new_expiration or None,
                    notes=new_notes,
                    max_users=new_max_users if selected_record["key_type"] == KEY_TYPE_LICENSE else None,
                    trial=new_trial if selected_record["key_type"] == KEY_TYPE_LICENSE else None,
                )
                st.success("Metadata updated.")
                st.rerun()

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Revoke key", key=f"revoke_{selected_record['id']}"):
                store.revoke_key(selected_record["id"])
                st.success("Key revoked.")
                st.rerun()
        with col2:
            if st.button("Enable key", key=f"enable_{selected_record['id']}"):
                store.toggle_key_status(selected_record["id"], is_active=True)
                st.success("Key enabled.")
                st.rerun()
        with col3:
            if st.button("Disable key", key=f"disable_{selected_record['id']}"):
                store.toggle_key_status(selected_record["id"], is_active=False)
                st.success("Key disabled.")
                st.rerun()

with tab_validate:
    st.subheader("Buyer Dashboard Validation Test")
    with st.form("local_validate"):
        api_key = st.text_input("API key to validate", type="password")
        check = st.form_submit_button("Validate API key")
        if check:
            result = store.validate_api_key(api_key)
            if result.get("valid"):
                st.success("API key is valid.")
            else:
                st.error(f"Invalid key: {result.get('reason')}")
            st.json(result)
