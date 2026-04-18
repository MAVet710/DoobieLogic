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

app_start = perf_counter()
st.set_page_config(page_title="DoobieLogic", page_icon="🌿", layout="wide")
logger.info("Streamlit rerun startup completed in %.4fs", perf_counter() - app_start)


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


for key, default in {
    "chat_history": [],
    "csv_active": False,
    "mapped_data": {},
    "file_insights": {},
    "buyer_brain": {},
    "uploaded_file_name": "",
    "uploaded_file_hash": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

copilot = get_copilot()

st.title("🌿 DoobieLogic Copilot")
st.caption("Department-aware cannabis operating copilot with curated learned knowledge and conservative grounded context.")

sidebar_start = perf_counter()
st.sidebar.header("Workspace")
persona = st.sidebar.selectbox("Role", ["buyer", "retail_ops", "compliance", "extraction", "executive"], key="persona_select")
state = st.sidebar.selectbox("State", sorted(REGULATION_LINKS.keys()), key="state_select")

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
logger.info("Sidebar rendered in %.4fs", perf_counter() - sidebar_start)

upload_start = perf_counter()
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
logger.info("Upload section completed in %.4fs", perf_counter() - upload_start)

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

quick_action = st.selectbox(
    "Quick actions",
    ["None", "slow movers", "reorder opportunities", "markdown candidates", "category risk"],
    key="quick_action_select",
)

prompt = st.text_area("Ask anything", placeholder="Why is my inventory not moving?", height=120, key="prompt_area")

if st.button("Ask DoobieLogic", type="primary", key="ask_button"):
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
                    persona=persona,
                    state=state,
                )
            else:
                response = copilot.ask(final_prompt, persona=persona, state=state)

            st.session_state.chat_history.append({"q": final_prompt, "res": asdict(response)})
        except Exception as exc:  # visible debug instead of white-screen failure
            st.error(f"Copilot error: {exc}")
        finally:
            logger.info("Ask action completed in %.4fs", perf_counter() - ask_started)

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
