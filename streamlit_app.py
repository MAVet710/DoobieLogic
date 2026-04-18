from __future__ import annotations

import hashlib
import logging
from dataclasses import asdict
from time import perf_counter
from typing import Any

import streamlit as st

from doobielogic.buyer_brain import render_buyer_brain_summary, summarize_buyer_opportunities
from doobielogic.copilot import DoobieCopilot
from doobielogic.parser import analyze_mapped_data, basic_cannabis_mapping, load_csv_bytes, render_insight_summary
from doobielogic.regulations import REGULATION_LINKS

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


def _record_timing(section: str, started: float) -> None:
    elapsed = perf_counter() - started
    if st.session_state.get("debug_timings", False):
        logs = st.session_state.get("timing_logs", [])
        logs.append(f"{section}: {elapsed:.4f}s")
        st.session_state.timing_logs = logs[-20:]


def _init_state() -> None:
    for key, default in {
        "chat_history": [],
        "csv_active": False,
        "mapped_data": {},
        "file_insights": {},
        "buyer_brain": {},
        "uploaded_file_name": "",
        "uploaded_file_hash": "",
        "persona": "buyer",
        "state": sorted(REGULATION_LINKS.keys())[0],
        "debug_timings": False,
        "timing_logs": [],
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default


@st.fragment
def render_sidebar_controls() -> None:
    st.sidebar.header("Workspace")
    st.sidebar.checkbox("Debug timings", key="debug_timings")
    st.sidebar.selectbox(
        "Role",
        ["buyer", "retail_ops", "compliance", "extraction", "executive"],
        key="persona",
    )
    st.sidebar.selectbox("State", sorted(REGULATION_LINKS.keys()), key="state")

    st.sidebar.subheader("File Controls")
    if st.sidebar.button("Clear file", key="clear_file_btn"):
        st.session_state.csv_active = False
        st.session_state.mapped_data = {}
        st.session_state.file_insights = {}
        st.session_state.buyer_brain = {}
        st.session_state.uploaded_file_name = ""
        st.session_state.uploaded_file_hash = ""

    if st.sidebar.button("Clear chat", key="clear_chat_btn"):
        st.session_state.chat_history = []


def main() -> None:
    st.set_page_config(page_title="DoobieLogic", page_icon="🌿", layout="wide")
    _init_state()
    copilot = get_copilot()
    render_sidebar_controls()

    st.title("🌿 DoobieLogic Copilot")
    st.caption("Department-aware cannabis operating copilot with curated learned knowledge and conservative grounded context.")

    upload_started = perf_counter()
    uploaded = st.file_uploader("Upload cannabis inventory CSV", type=["csv"], key="inventory_csv_uploader")
    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        is_new_upload = (
            uploaded.name != st.session_state.uploaded_file_name
            or file_hash != st.session_state.uploaded_file_hash
            or not st.session_state.csv_active
        )

        if is_new_upload:
            with st.spinner("Processing uploaded CSV..."):
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
                st.session_state.uploaded_file_hash = file_hash
    _record_timing("upload_section", upload_started)

    if st.session_state.csv_active:
        st.success(f"CSV active: {st.session_state.uploaded_file_name}")
    else:
        st.caption("No CSV active. Upload a file to unlock file intelligence and buyer-brain insights.")

    file_intel_container = st.empty()
    buyer_brain_container = st.empty()
    chat_history_container = st.empty()

    render_file_started = perf_counter()
    with file_intel_container.container():
        with st.expander("📈 File Intelligence", expanded=True):
            st.markdown(render_insight_summary(st.session_state.file_insights))
    _record_timing("file_intelligence_render", render_file_started)

    render_buyer_started = perf_counter()
    with buyer_brain_container.container():
        if st.session_state.buyer_brain:
            st.markdown("### 🛒 Buyer Brain")
            st.markdown(render_buyer_brain_summary(st.session_state.buyer_brain))
    _record_timing("buyer_brain_render", render_buyer_started)

    form_started = perf_counter()
    with st.form("ask_form", clear_on_submit=False):
        quick_action = st.selectbox(
            "Quick actions",
            ["None", "slow movers", "reorder opportunities", "markdown candidates", "category risk"],
            key="quick_action_select",
        )
        prompt = st.text_area("Ask anything", placeholder="Why is my inventory not moving?", height=120, key="prompt_area")
        submitted = st.form_submit_button("Ask DoobieLogic", type="primary")
    _record_timing("ask_form_render", form_started)

    if submitted:
        ask_started = perf_counter()
        final_prompt = prompt.strip()
        if quick_action != "None":
            final_prompt = (final_prompt + "\n\n" if final_prompt else "") + f"Quick action focus: {quick_action}."

        if not final_prompt:
            st.warning("Please enter a question or select a quick action.")
        else:
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
            except Exception as exc:  # visible debug instead of white-screen failure
                st.error(f"Copilot error: {exc}")
        _record_timing("ask_submit", ask_started)

    chat_started = perf_counter()
    with chat_history_container.container():
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
    _record_timing("chat_render", chat_started)

    if st.session_state.debug_timings:
        with st.sidebar.expander("Timing debug", expanded=False):
            for row in st.session_state.timing_logs:
                st.caption(row)


if __name__ == "__main__":
    main()
