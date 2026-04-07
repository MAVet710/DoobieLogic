from __future__ import annotations

from dataclasses import asdict

import streamlit as st

from doobielogic.copilot import DoobieCopilot
from doobielogic.parser import analyze_mapped_data, basic_cannabis_mapping, load_csv_bytes, render_insight_summary
from doobielogic.buyer_brain import render_buyer_brain_summary, summarize_buyer_opportunities
from doobielogic.regulations import REGULATION_LINKS

st.set_page_config(page_title="DoobieLogic", page_icon="🌿", layout="wide")

if "copilot" not in st.session_state:
    st.session_state.copilot = DoobieCopilot()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "csv_active" not in st.session_state:
    st.session_state.csv_active = False
if "mapped_data" not in st.session_state:
    st.session_state.mapped_data = {}
if "file_insights" not in st.session_state:
    st.session_state.file_insights = {}
if "buyer_brain" not in st.session_state:
    st.session_state.buyer_brain = {}
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = ""

copilot = st.session_state.copilot

st.title("🌿 DoobieLogic Copilot")
st.caption("Ask, analyze, verify, and act across cannabis operations.")

st.sidebar.header("Workspace")
persona = st.sidebar.selectbox("Role", ["buyer", "retail_ops", "compliance", "extraction", "executive"])
state = st.sidebar.selectbox("State", sorted(REGULATION_LINKS.keys()))

st.sidebar.subheader("File Controls")
if st.sidebar.button("Clear file"):
    st.session_state.csv_active = False
    st.session_state.mapped_data = {}
    st.session_state.file_insights = {}
    st.session_state.buyer_brain = {}
    st.session_state.uploaded_file_name = ""

if st.sidebar.button("Clear chat"):
    st.session_state.chat_history = []

uploaded = st.file_uploader("Upload cannabis inventory CSV", type=["csv"])
if uploaded is not None:
    df = load_csv_bytes(uploaded.getvalue())
    if df is None:
        st.error("Could not parse CSV. Please upload a valid comma-separated file.")
    else:
        mapped_data = basic_cannabis_mapping(df)
        st.session_state.csv_active = True
        st.session_state.mapped_data = mapped_data
        st.session_state.file_insights = analyze_mapped_data(mapped_data)
        st.session_state.buyer_brain = summarize_buyer_opportunities(mapped_data)
        st.session_state.uploaded_file_name = uploaded.name

if st.session_state.csv_active:
    st.success(f"CSV active: {st.session_state.uploaded_file_name}")
else:
    st.caption("No CSV active. Upload a file to unlock file intelligence and buyer-brain insights.")

with st.expander("📈 File Intelligence", expanded=True):
    st.markdown(render_insight_summary(st.session_state.file_insights))
    if st.session_state.buyer_brain:
        st.markdown(render_buyer_brain_summary(st.session_state.buyer_brain))

quick_action = st.selectbox(
    "Quick actions",
    ["None", "slow movers", "reorder opportunities", "markdown candidates", "category risk"],
)

prompt = st.text_area("Ask anything", placeholder="Why is my inventory not moving?", height=120)

if st.button("Ask DoobieLogic", type="primary"):
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
                    persona=persona,
                    state=state,
                )
            else:
                response = copilot.ask(final_prompt, persona=persona, state=state)

            st.session_state.chat_history.append({"q": final_prompt, "res": asdict(response)})
        except Exception as exc:  # visible debug instead of white-screen failure
            st.error(f"Copilot error: {exc}")

for item in reversed(st.session_state.chat_history):
    res = item.get("res")
    if res is None:
        continue

    st.markdown("---")
    st.markdown(f"**You:** {item.get('q', '')}")

    st.markdown("### 🧠 Answer")
    st.write(getattr(res, "answer", "No answer available."))

    st.markdown("### ⚠️ Confidence")
    confidence = str(getattr(res, "confidence", "unknown")).upper()
    st.write(confidence)

    st.markdown("### 🔍 Grounding")
    st.write(getattr(res, "grounding", "No grounding data available."))

    sources = getattr(res, "sources", []) or []
    if sources:
        st.markdown("### 📚 Sources")
        for s in sources:
            st.write(f"- {s}")

    suggestions = getattr(res, "suggestions", []) or []
    if suggestions:
        st.markdown("### ⚡ Next Moves")
        for s in suggestions:
            st.write(f"- {s}")
