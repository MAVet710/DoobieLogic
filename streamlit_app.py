from __future__ import annotations

import logging
import os
from dataclasses import asdict
from time import perf_counter
from typing import Any

import streamlit as st

from doobielogic.admin_auth import AdminAuthConfig, load_admin_auth_config
from doobielogic.buyer_brain import summarize_buyer_opportunities
from doobielogic.config import load_doobie_config
from doobielogic.compliance_answers import answer_verified_compliance_question, unverified_compliance_result
from doobielogic.conversational_ai import ConversationService
from doobielogic.copilot import DoobieCopilot
from doobielogic.intelligence_router import IntelligenceRoute, infer_intelligence_route
from doobielogic.jurisdictions import (
    compliance_clarification_result,
    get_jurisdiction_context,
    infer_jurisdiction_code,
)
from doobielogic.operational_answers import answer_operational_question
from doobielogic.parser import analyze_mapped_data, basic_cannabis_mapping, load_csv_bytes
from doobielogic.ui_theme import apply_chat_theme
from doobielogic.user_management import (
    VALID_PERMISSIONS,
    UserRecord,
    UserStore,
    hash_password,
    verify_password,
)


logger = logging.getLogger("doobielogic.streamlit")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


@st.cache_resource
def get_copilot() -> DoobieCopilot:
    return DoobieCopilot()


@st.cache_resource
def get_conversation_service() -> ConversationService:
    return ConversationService()


@st.cache_resource
def get_user_store(database_url: str, sqlite_path: str) -> UserStore:
    return UserStore(database_url=database_url, sqlite_path=sqlite_path)


@st.cache_data(show_spinner=False)
def process_csv(file_bytes: bytes) -> tuple[dict[str, list[Any]] | None, dict[str, Any], dict[str, Any]]:
    rows = load_csv_bytes(file_bytes)
    if rows is None:
        return None, {}, {}
    mapped_data = basic_cannabis_mapping(rows)
    return mapped_data, analyze_mapped_data(mapped_data), summarize_buyer_opportunities(mapped_data)


def _safe_secrets() -> dict[str, Any]:
    try:
        return st.secrets.to_dict() if hasattr(st, "secrets") else {}
    except Exception:
        return {}


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "on"}


def _initialize_session_state() -> None:
    defaults = {
        "chat_history": [],
        "mapped_data": {},
        "file_insights": {},
        "buyer_brain": {},
        "uploaded_file_name": "",
        "uploaded_file_token": "",
        "jurisdiction": None,
        "workspace": "chat",
        "auth_user_id": None,
        "auth_username": None,
        "auth_display_name": None,
        "auth_user_role": None,
        "auth_must_change_password": False,
        "authenticated": False,
        "pending_prompt": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _current_user(store: UserStore) -> UserRecord | None:
    username = st.session_state.get("auth_username")
    return store.get_user(username) if username else None


def _apply_user_session(user: UserRecord) -> None:
    st.session_state.authenticated = True
    st.session_state.auth_user_id = user.id
    st.session_state.auth_username = user.username
    st.session_state.auth_display_name = user.display_name or user.username
    st.session_state.auth_user_role = user.role
    st.session_state.auth_must_change_password = user.must_change_password


def _clear_user_session() -> None:
    for key, value in {
        "authenticated": False,
        "auth_user_id": None,
        "auth_username": None,
        "auth_display_name": None,
        "auth_user_role": None,
        "auth_must_change_password": False,
        "workspace": "chat",
    }.items():
        st.session_state[key] = value


def _bootstrap_admin(store: UserStore, config: AdminAuthConfig) -> None:
    if config.username and config.password_hash:
        store.ensure_bootstrap_admin(config.username, config.password_hash)


def _render_first_run_setup(store: UserStore) -> bool:
    configured_token = str(os.environ.get("DOOBIE_BOOTSTRAP_TOKEN") or "").strip()
    if not configured_token:
        st.error(
            "No administrator exists. Set DOOBIE_BOOTSTRAP_TOKEN once, restart the app, "
            "and create the owner account here."
        )
        return False

    st.markdown("<div class='dl-auth-card'>", unsafe_allow_html=True)
    st.markdown("## Create the first administrator")
    st.caption("This one-time setup creates a bcrypt-protected owner account in the shared database.")
    with st.form("first_run_admin", clear_on_submit=True):
        setup_token = st.text_input("Setup token", type="password")
        username = st.text_input("Administrator username")
        display_name = st.text_input("Display name")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create administrator", type="primary")
    st.markdown("</div>", unsafe_allow_html=True)

    if not submitted:
        return False
    if setup_token != configured_token:
        st.error("The setup token is invalid.")
    elif password != confirm:
        st.error("The passwords do not match.")
    else:
        try:
            user = store.create_user(
                username=username,
                display_name=display_name,
                password_hash=hash_password(password),
                role="admin",
                created_by="first-run-setup",
                must_change_password=False,
            )
            _apply_user_session(user)
            st.success("Administrator created.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to create the administrator: {exc}")
    return False


def _render_login(store: UserStore, auth_config: AdminAuthConfig) -> bool:
    _bootstrap_admin(store, auth_config)
    users = store.list_users()
    login_required = _truthy(os.environ.get("DOOBIE_REQUIRE_LOGIN")) or bool(users)

    if st.session_state.authenticated:
        user = _current_user(store)
        if user and user.active:
            _apply_user_session(user)
            return True
        _clear_user_session()

    if not login_required:
        st.session_state.auth_user_role = "analyst"
        st.session_state.auth_display_name = "Guest"
        return True

    if not users:
        return _render_first_run_setup(store)

    left, center, right = st.columns([1, 1.2, 1])
    with center:
        st.markdown("<div class='dl-auth-card'>", unsafe_allow_html=True)
        st.markdown("## Welcome to DoobieLogic")
        st.caption("Sign in to your cannabis intelligence workspace.")
        with st.form("doobie_login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    if submitted:
        user = store.authenticate(username, password)
        if user:
            _apply_user_session(user)
            st.rerun()
        st.error("Invalid username or password.")
    return False


def _render_required_password_change(store: UserStore) -> bool:
    if not st.session_state.get("auth_must_change_password"):
        return True
    st.warning("Your temporary password must be replaced before you continue.")
    with st.form("required_password_change", clear_on_submit=True):
        password = st.text_input("New password", type="password")
        confirm = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button("Save new password", type="primary")
    if submitted:
        if password != confirm:
            st.error("The passwords do not match.")
        else:
            try:
                changed = store.change_password(st.session_state.auth_user_id, hash_password(password))
            except ValueError as exc:
                st.error(str(exc))
            else:
                if changed:
                    st.session_state.auth_must_change_password = False
                    st.success("Password updated.")
                    st.rerun()
                st.error("The password could not be updated.")
    return False


def _current_permissions(store: UserStore) -> set[str]:
    role = store.get_role(st.session_state.get("auth_user_role") or "analyst")
    return set(role.permissions) if role else {"chat"}


def _handle_upload(uploaded: Any) -> None:
    if uploaded is None:
        return
    token = f"{getattr(uploaded, 'file_id', 'file')}::{uploaded.name}::{uploaded.size}"
    if token == st.session_state.uploaded_file_token:
        return
    mapped, insights, buyer = process_csv(uploaded.getvalue())
    if mapped is None:
        st.error("That CSV could not be parsed.")
        return
    st.session_state.mapped_data = mapped
    st.session_state.file_insights = insights
    st.session_state.buyer_brain = buyer
    st.session_state.uploaded_file_name = uploaded.name
    st.session_state.uploaded_file_token = token


def _clear_file() -> None:
    for key, value in {
        "mapped_data": {},
        "file_insights": {},
        "buyer_brain": {},
        "uploaded_file_name": "",
        "uploaded_file_token": "",
    }.items():
        st.session_state[key] = value


def _render_sidebar(store: UserStore, permissions: set[str]) -> None:
    st.sidebar.markdown("<div class='dl-brand'>🌿 <strong>DoobieLogic</strong></div>", unsafe_allow_html=True)
    if st.sidebar.button("＋ New chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.workspace = "chat"
        st.rerun()

    if st.sidebar.button("Cannabis AI", use_container_width=True):
        st.session_state.workspace = "chat"
        st.rerun()
    if "view_admin" in permissions and st.sidebar.button("Admin console", use_container_width=True):
        st.session_state.workspace = "admin"
        st.rerun()

    if "upload_data" in permissions:
        uploaded = st.sidebar.file_uploader(
            "Add business data",
            type=["csv"],
            help="Upload inventory, sales, cultivation, extraction, manufacturing, packaging, or compliance data.",
        )
        _handle_upload(uploaded)
        if st.session_state.uploaded_file_name:
            st.sidebar.success(st.session_state.uploaded_file_name)
            if st.sidebar.button("Remove data", use_container_width=True):
                _clear_file()
                st.rerun()

    st.sidebar.markdown("---")
    identity = st.session_state.get("auth_display_name") or "Guest"
    st.sidebar.caption(identity)
    if st.session_state.authenticated and st.sidebar.button("Log out", use_container_width=True):
        _clear_user_session()
        st.rerun()


def _run_copilot(
    prompt: str,
    route: IntelligenceRoute,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    copilot = get_copilot()
    data = st.session_state.mapped_data or {}
    resolved_prompt = prompt
    if route.reason == "Continued the prior compliance question":
        for message in reversed(history or []):
            if message.get("role") == "user" and str(message.get("content") or "").strip():
                resolved_prompt = f"{message['content']}\nJurisdiction: {prompt}"
                break
    inferred_state = infer_jurisdiction_code(prompt)
    if inferred_state:
        st.session_state.jurisdiction = inferred_state
    state = st.session_state.jurisdiction
    if route.mode == "compliance" and not state:
        return compliance_clarification_result(route.label)
    if route.mode == "compliance":
        verified = answer_verified_compliance_question(resolved_prompt, state)
        if verified:
            return get_conversation_service().enhance(
                verified,
                question=resolved_prompt,
                mode=route.mode,
                state=state,
                data=data,
                history=history,
            )
    playbook = answer_operational_question(resolved_prompt, route.mode)
    if playbook and route.mode != "compliance":
        playbook["route_label"] = route.label
        playbook["routed_by"] = route.reason
        return get_conversation_service().enhance(
            playbook,
            question=resolved_prompt,
            mode=playbook.get("mode", route.mode),
            state=state,
            data=data,
            history=history,
        )
    if route.mode == "compliance":
        unverified = unverified_compliance_result(resolved_prompt, state)
        unverified["route_label"] = route.label
        unverified["routed_by"] = route.reason
        return get_conversation_service().enhance(
            unverified,
            question=resolved_prompt,
            mode=route.mode,
            state=state,
            data=data,
            history=history,
        )
    if route.mode == "buyer":
        response = copilot.ask_with_buyer_brain(
            resolved_prompt,
            mapped_data=data,
            persona="buyer",
            state=state,
        )
    elif route.mode in {
        "retail_ops",
        "cultivation",
        "extraction",
        "kitchen",
        "packaging",
        "ops",
        "compliance",
    }:
        department = "operations" if route.mode == "ops" else route.mode
        response = copilot.ask_with_operations(
            resolved_prompt,
            department=department,
            parsed_data=data,
            persona=route.mode,
            state=state,
        )
    else:
        response = copilot.ask(resolved_prompt, persona=route.mode, state=state)

    result = asdict(response)
    result["routed_mode"] = route.mode
    result["route_label"] = route.label
    result["routed_by"] = route.reason
    if route.mode == "compliance":
        context = get_jurisdiction_context(state)
        result["compliance_context"] = context.to_dict() if context else None
    return get_conversation_service().enhance(
        result,
        question=resolved_prompt,
        mode=route.mode,
        state=state,
        data=data,
        history=history,
    )


def _render_assistant_message(result: dict[str, Any]) -> None:
    st.markdown(result.get("answer") or "I could not produce an answer.")
    route_label = result.get("route_label")
    if route_label:
        st.caption(f"Automatically routed to {route_label} · {str(result.get('confidence', 'low')).title()} confidence")

    with st.expander("Sources, reasoning, and next actions"):
        ai = result.get("ai") or {}
        if ai.get("enabled"):
            st.caption(f"Conversation model: {ai.get('provider')} / {ai.get('model')}")
        elif ai.get("fallback_reason"):
            st.caption(f"Conversation layer: rules-engine fallback ({ai.get('fallback_reason')})")
        explanation = result.get("explanation")
        if explanation:
            st.markdown("#### Why")
            st.write(explanation)
        recommendations = result.get("recommendations") or []
        if recommendations:
            st.markdown("#### Next actions")
            for item in recommendations:
                st.markdown(f"- {item}")
        risk_flags = result.get("risk_flags") or []
        if risk_flags:
            st.markdown("#### Risk flags")
            for item in risk_flags:
                st.markdown(f"- {item}")
        sources = result.get("sources") or []
        if sources:
            st.markdown("#### Sources")
            for source in sources:
                st.markdown(f"- {source}")
        compliance = result.get("compliance_context")
        if compliance:
            st.markdown("#### Compliance grounding")
            st.write(
                f"{compliance.get('jurisdiction')} · {compliance.get('scope_label')} · "
                f"updated {compliance.get('last_updated')} · {compliance.get('review_status')}"
            )


def _render_empty_chat() -> None:
    st.markdown(
        """
        <div class="dl-welcome">
            <div class="dl-welcome-mark">🌿</div>
            <h1>How can I help your cannabis business?</h1>
            <p>Ask about retail, buying, inventory, cultivation, extraction, manufacturing,
            packaging, finance, operations, or state-specific compliance.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    prompts = (
        "What should I review before placing this week's purchase orders?",
        "How can I improve extraction yield without creating compliance risk?",
        "Build a cultivation room performance review checklist.",
        "What packaging and labeling controls should I verify in my jurisdiction?",
    )
    columns = st.columns(2)
    for index, suggestion in enumerate(prompts):
        with columns[index % 2]:
            if st.button(suggestion, key=f"starter_{index}", use_container_width=True):
                st.session_state.pending_prompt = suggestion
                st.rerun()


def _render_chat(store: UserStore) -> None:
    if not st.session_state.chat_history:
        _render_empty_chat()
    else:
        for message in st.session_state.chat_history:
            role = message.get("role", "assistant")
            with st.chat_message(role):
                if role == "assistant":
                    _render_assistant_message(message.get("result") or {})
                else:
                    st.markdown(message.get("content") or "")

    pending = str(st.session_state.pop("pending_prompt", "") or "").strip()
    prompt = st.chat_input("Message DoobieLogic")
    final_prompt = pending or str(prompt or "").strip()
    if not final_prompt:
        return

    st.session_state.chat_history.append({"role": "user", "content": final_prompt})
    route = infer_intelligence_route(
        final_prompt,
        data=st.session_state.mapped_data,
        user_role=st.session_state.get("auth_user_role"),
    )
    if (
        route.mode != "compliance"
        and len(st.session_state.chat_history) >= 2
        and (st.session_state.chat_history[-2].get("result") or {}).get("needs_clarification")
        and infer_jurisdiction_code(final_prompt)
    ):
        route = IntelligenceRoute("compliance", "Compliance", "Continued the prior compliance question")
    with st.spinner(f"Working across {route.label.lower()} knowledge..."):
        try:
            result = _run_copilot(
                final_prompt,
                route,
                history=st.session_state.chat_history[:-1],
            )
        except Exception:
            logger.exception("Copilot request failed")
            result = {
                "answer": "I hit an internal error while processing that request.",
                "confidence": "low",
                "route_label": route.label,
                "recommendations": ["Try again or ask an administrator to review the service logs."],
            }
    st.session_state.chat_history.append({"role": "assistant", "result": result})
    st.rerun()


def _render_profile_password(store: UserStore) -> None:
    if not st.session_state.authenticated:
        return
    with st.expander("Change my password"):
        with st.form("profile_change_password", clear_on_submit=True):
            current_password = st.text_input("Current password", type="password")
            password = st.text_input("New password", type="password")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Update password")
        if submitted:
            current_user = _current_user(store)
            if not current_user or not verify_password(current_password, current_user.password_hash):
                st.error("The current password is incorrect.")
            elif password != confirm:
                st.error("The passwords do not match.")
            else:
                try:
                    changed = store.change_password(st.session_state.auth_user_id, hash_password(password))
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success("Password updated." if changed else "Password could not be updated.")


def _render_user_admin(store: UserStore) -> None:
    users = store.list_users()
    roles = store.list_roles()
    st.dataframe(
        [
            {
                "Username": user.username,
                "Display name": user.display_name,
                "Email": user.email,
                "Role": user.role,
                "Active": user.active,
                "Password change required": user.must_change_password,
                "Last login": user.last_login_at,
            }
            for user in users
        ],
        hide_index=True,
        use_container_width=True,
    )

    create_tab, manage_tab = st.tabs(["Create user", "Manage existing"])
    with create_tab:
        with st.form("create_doobie_user", clear_on_submit=True):
            left, right = st.columns(2)
            username = left.text_input("Username")
            display_name = right.text_input("Display name")
            email = left.text_input("Email (optional)")
            role = right.selectbox("Role", [item.name for item in roles])
            password = left.text_input("Temporary password", type="password")
            confirm = right.text_input("Confirm temporary password", type="password")
            must_change = st.checkbox("Require password change at first sign-in", value=True)
            submitted = st.form_submit_button("Create user", type="primary")
        if submitted:
            if password != confirm:
                st.error("The passwords do not match.")
            else:
                try:
                    store.create_user(
                        username=username,
                        display_name=display_name,
                        email=email,
                        password_hash=hash_password(password),
                        role=role,
                        created_by=st.session_state.auth_username or "admin",
                        must_change_password=must_change,
                    )
                    st.success(f"User '{username}' created.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Unable to create user: {exc}")

    with manage_tab:
        if not users:
            st.info("Create a user first.")
            return
        by_name = {user.username: user for user in users}
        selected_name = st.selectbox("User", list(by_name), key="manage_existing_user")
        selected = by_name[selected_name]
        active = st.checkbox("Account active", value=selected.active)
        role_names = [item.name for item in roles]
        selected_role = st.selectbox(
            "Assigned role",
            role_names,
            index=role_names.index(selected.role),
            key=f"manage_existing_user_role_{selected.id}",
        )
        if st.button("Save account and role"):
            if selected.id == st.session_state.auth_user_id and (
                not active or selected_role != selected.role
            ):
                st.error("You cannot deactivate or change the role of your current account.")
            else:
                actor = st.session_state.auth_username or "admin"
                status_saved = store.set_active(selected.id, active, actor)
                role_saved = store.set_role(selected.id, selected_role, actor)
                if status_saved and role_saved:
                    st.success("Account status and role updated.")
                    st.rerun()
        with st.form("admin_reset_password", clear_on_submit=True):
            password = st.text_input("New temporary password", type="password")
            confirm = st.text_input("Confirm temporary password", type="password")
            submitted = st.form_submit_button("Reset password")
        if submitted:
            if password != confirm:
                st.error("The passwords do not match.")
            else:
                try:
                    reset = store.reset_password(
                        selected.id,
                        hash_password(password),
                        st.session_state.auth_username or "admin",
                    )
                    st.success(
                        "Password reset; a change will be required at next sign-in."
                        if reset
                        else "Password could not be reset."
                    )
                except ValueError as exc:
                    st.error(str(exc))


def _render_role_admin(store: UserStore) -> None:
    roles = store.list_roles(active_only=False)
    st.dataframe(
        [
            {
                "Role": role.name,
                "Display name": role.display_name,
                "Permissions": ", ".join(role.permissions),
                "System role": role.system_role,
                "Active": role.active,
            }
            for role in roles
        ],
        hide_index=True,
        use_container_width=True,
    )
    with st.form("create_doobie_role", clear_on_submit=True):
        name = st.text_input("Role name", help="Lowercase letters, numbers, underscores, and hyphens.")
        display_name = st.text_input("Display name")
        permissions = st.multiselect(
            "Permissions",
            sorted(VALID_PERMISSIONS),
            default=["chat"],
        )
        submitted = st.form_submit_button("Create role", type="primary")
    if submitted:
        try:
            store.create_role(name=name, display_name=display_name, permissions=permissions)
            st.success(f"Role '{name}' created.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to create role: {exc}")


def _render_admin_console(store: UserStore, permissions: set[str]) -> None:
    st.markdown("## Admin console")
    st.caption("Manage secure accounts, password lifecycle, and role-based access.")
    tabs: list[str] = []
    if "manage_users" in permissions:
        tabs.append("Users")
    if "manage_roles" in permissions:
        tabs.append("Roles")
    tabs.append("My security")
    tab_objects = st.tabs(tabs)
    for label, tab_object in zip(tabs, tab_objects):
        with tab_object:
            if label == "Users":
                _render_user_admin(store)
            elif label == "Roles":
                _render_role_admin(store)
            else:
                _render_profile_password(store)


def main() -> None:
    started = perf_counter()
    st.set_page_config(
        page_title="DoobieLogic Cannabis AI",
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_chat_theme()
    _initialize_session_state()

    config = load_doobie_config()
    try:
        store = get_user_store(
            config.database_url,
            os.environ.get("DOOBIE_USER_DB", "data/user_store.db"),
        )
    except Exception:
        logger.exception("User store initialization failed")
        st.error("Secure user storage could not be initialized. Check the database configuration.")
        st.stop()

    auth_config = load_admin_auth_config(_safe_secrets(), os.environ)
    if not _render_login(store, auth_config):
        st.stop()
    if not _render_required_password_change(store):
        st.stop()

    permissions = _current_permissions(store)
    _render_sidebar(store, permissions)
    if st.session_state.workspace == "admin" and "view_admin" in permissions:
        _render_admin_console(store, permissions)
    else:
        _render_chat(store)
    logger.info("Streamlit render completed in %.4fs", perf_counter() - started)


if __name__ == "__main__":
    main()
