from __future__ import annotations

import logging
from dataclasses import asdict
from time import perf_counter
from typing import Any

import streamlit as st

from doobielogic.admin_auth import SESSION_AUTH_KEY, logout_admin, require_admin_auth
from doobielogic.buyer_brain import render_buyer_brain_summary, summarize_buyer_opportunities
from doobielogic.copilot import DoobieCopilot
from doobielogic.parser import analyze_mapped_data, basic_cannabis_mapping, load_csv_bytes, render_insight_summary
from doobielogic.regulations import REGULATION_LINKS
from doobielogic.ui_theme import apply_buyer_dashboard_theme, render_page_hero, section_close, section_open

logger = logging.getLogger("doobielogic.streamlit")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

@st.cache_resource
def get_copilot() -> DoobieCopilot:
    started = perf_counter()
    copilot = DoobieCopilot()
    logger.info("Copilot initialized in %.4fs", perf_counter() - started)
    return copilot


@st.cache_data(show_spinner=False)
def process_csv(file_bytes: bytes) -> tuple[dict[str, list[Any]] | None, dict[str, Any], dict[str, Any]]:
    started = perf_counter()
    rows = load_csv_bytes(file_bytes)
    if rows is None:
        logger.info("CSV parse failed in %.4fs", perf_counter() - started)
        return None, {}, {}

    mapped_data = basic_cannabis_mapping(rows)
    insights = analyze_mapped_data(mapped_data)
    buyer = summarize_buyer_opportunities(mapped_data)
    logger.info("CSV processing completed in %.4fs", perf_counter() - started)
    return mapped_data, insights, buyer


def _initialize_session_state() -> None:
    defaults = {
        "chat_history": [],
        "csv_active": False,
        "mapped_data": {},
        "file_insights": {},
        "buyer_brain": {},
        "uploaded_file_name": "",
        "uploaded_file_token": "",
        "persona": "buyer",
        "state": sorted(REGULATION_LINKS.keys())[0],
        SESSION_AUTH_KEY: False,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default




def _handle_upload() -> None:
    upload_start = perf_counter()
    uploaded = st.file_uploader("Upload cannabis inventory CSV", type=["csv"], key="inventory_csv_uploader")
    if uploaded is None:
        logger.info("Upload section completed in %.4fs (no upload)", perf_counter() - upload_start)
        return

    upload_token = f"{getattr(uploaded, 'file_id', 'no-file-id')}::{uploaded.name}::{uploaded.size}"
    is_new_upload = (
        upload_token != st.session_state.uploaded_file_token
        or uploaded.name != st.session_state.uploaded_file_name
        or not st.session_state.csv_active
    )
    if is_new_upload:
        with st.spinner("Processing uploaded CSV..."):
            file_bytes = uploaded.getvalue()
            mapped_data, insights, buyer = process_csv(file_bytes)
        if mapped_data is None:
            st.error("Could not parse CSV. Please upload a valid comma-separated file.")
            st.session_state.csv_active = False
        else:
            st.session_state.csv_active = True
            st.session_state.mapped_data = mapped_data
            st.session_state.file_insights = insights
            st.session_state.buyer_brain = buyer
            st.session_state.uploaded_file_name = uploaded.name
            st.session_state.uploaded_file_token = upload_token
    logger.info(
        "Upload section completed in %.4fs (new_upload=%s)",
        perf_counter() - upload_start,
        is_new_upload,
    )


def _render_chat_history() -> None:
    chat_render_start = perf_counter()
    for item in reversed(st.session_state.chat_history):
        res = item.get("res")
        if not isinstance(res, dict):
            continue

        st.markdown("---")
        st.markdown(f"**You:** {item.get('q', '')}")

        st.markdown("### 🧠 Answer")
        st.write(res.get("answer", "No answer available."))

        st.markdown("### ⚠️ Confidence")
        st.write(str(res.get("confidence", "unknown")).upper())

        explanation = res.get("explanation")
        if explanation:
            st.markdown("### 🧾 Explanation")
            st.write(explanation)

        sources = res.get("sources", []) or []
        if sources:
            st.markdown("### 📚 Sources")
            for source in sources:
                st.write(f"- {source}")

        recommendations = res.get("recommendations", []) or []
        if recommendations:
            st.markdown("### ⚡ Next Moves")
            for recommendation in recommendations:
                st.write(f"- {recommendation}")
    logger.info("Chat history rendered in %.4fs", perf_counter() - chat_render_start)


def main() -> None:
    app_start = perf_counter()
    st.set_page_config(page_title="DoobieLogic", page_icon="🌿", layout="wide")
    _initialize_session_state()
    st.session_state["_rerun_count"] = int(st.session_state.get("_rerun_count", 0)) + 1
    logger.info("Streamlit rerun #%s startup completed in %.4fs", st.session_state["_rerun_count"], perf_counter() - app_start)

    apply_buyer_dashboard_theme()
    render_page_hero(
        "🌿 DoobieLogic Copilot",
        "Department-aware cannabis operating copilot aligned to Buyer Dashboard design language.",
    )
    st.markdown(
        "<span class='dl-pill dl-pill-accent'>Live Copilot</span><span class='dl-pill dl-pill-success'>Buyer Dashboard Styled</span>",
        unsafe_allow_html=True,
    )

    if not require_admin_auth(form_key="app_admin_login", submit_label="Sign in"):
        st.stop()

    copilot = get_copilot()

    sidebar_start = perf_counter()
    st.sidebar.header("Workspace")
    with st.sidebar:
        logout_admin(button_key="app_admin_logout")
    persona_options = ["buyer", "retail_ops", "compliance", "extraction", "executive"]
    if st.session_state.persona not in persona_options:
        st.session_state.persona = "buyer"
    st.session_state.persona = st.sidebar.selectbox(
        "Role",
        persona_options,
        index=persona_options.index(st.session_state.persona),
        key="persona_select",
    )
    state_options = sorted(REGULATION_LINKS.keys())
    if st.session_state.state not in state_options:
        st.session_state.state = state_options[0]
    st.session_state.state = st.sidebar.selectbox(
        "State",
        state_options,
        index=state_options.index(st.session_state.state),
        key="state_select",
    )

    st.sidebar.subheader("File Controls")
    if st.sidebar.button("Clear file", key="clear_file_btn"):
        st.session_state.csv_active = False
        st.session_state.mapped_data = {}
        st.session_state.file_insights = {}
        st.session_state.buyer_brain = {}
        st.session_state.uploaded_file_name = ""
        st.session_state.uploaded_file_token = ""

    if st.sidebar.button("Clear chat", key="clear_chat_btn"):
        st.session_state.chat_history = []
    logger.info("Sidebar rendered in %.4fs", perf_counter() - sidebar_start)

    section_open()
    st.subheader("Upload & Data Context")
    _handle_upload()
    st.markdown("<div class='dl-kpi-grid'>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='dl-kpi'><div class='dl-kpi-label'>CSV Status</div><div class='dl-kpi-value'>{'Active' if st.session_state.csv_active else 'Idle'}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='dl-kpi'><div class='dl-kpi-label'>Persona</div><div class='dl-kpi-value'>{st.session_state.persona.title()}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='dl-kpi'><div class='dl-kpi-label'>Regulatory State</div><div class='dl-kpi-value'>{st.session_state.state}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.csv_active:
        st.success(f"CSV active: {st.session_state.uploaded_file_name}")
    else:
        st.caption("No CSV active. Upload a file to unlock file intelligence and buyer-brain insights.")

    intel_render_start = perf_counter()
    with st.expander("📈 File Intelligence", expanded=True):
        st.markdown(render_insight_summary(st.session_state.file_insights))
        if st.session_state.buyer_brain:
            st.markdown(render_buyer_brain_summary(st.session_state.buyer_brain))
    logger.info("File intelligence section rendered in %.4fs", perf_counter() - intel_render_start)
    section_close()

    section_open()
    st.subheader("Ask DoobieLogic")
    with st.form("ask_copilot_form", clear_on_submit=False):
        quick_action = st.selectbox(
            "Quick actions",
            ["None", "slow movers", "reorder opportunities", "markdown candidates", "category risk"],
            key="quick_action_select",
        )
        prompt = st.text_area("Ask anything", placeholder="Why is my inventory not moving?", height=120, key="prompt_area")
        submitted = st.form_submit_button("Ask DoobieLogic", type="primary")
    section_close()

    if submitted:
        final_prompt = prompt.strip()
        if quick_action != "None":
            final_prompt = (final_prompt + "\n\n" if final_prompt else "") + f"Quick action focus: {quick_action}."

        if not final_prompt:
            st.warning("Please enter a question or select a quick action.")
        else:
            ask_started = perf_counter()
            try:
                if st.session_state.mapped_data:
                    response = copilot.ask_with_buyer_brain(
                        final_prompt,
                        mapped_data=st.session_state.mapped_data,
                        persona=st.session_state.persona,
                        state=st.session_state.state,
                    )
                else:
                    response = copilot.ask(final_prompt, persona=st.session_state.persona, state=st.session_state.state)

                st.session_state.chat_history.append({"q": final_prompt, "res": asdict(response)})
            except Exception:  # visible debug instead of white-screen failure
                logger.exception("Copilot ask flow failed")
                st.error("Copilot error. Check server logs for traceback details.")
            finally:
                logger.info("Ask action completed in %.4fs", perf_counter() - ask_started)

    section_open()
    st.subheader("Conversation History")
    _render_chat_history()
    section_close()


if __name__ == "__main__":
    main()
