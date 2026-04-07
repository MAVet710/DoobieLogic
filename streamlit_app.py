from __future__ import annotations

import streamlit as st
from doobielogic.copilot import DoobieCopilot
from doobielogic.regulations import REGULATION_LINKS

st.set_page_config(page_title="DoobieLogic", page_icon="🌿", layout="wide")



# Init
if "copilot" not in st.session_state:
    st.session_state.copilot = DoobieCopilot()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

copilot = st.session_state.copilot

# Header
st.title("🌿 DoobieLogic Copilot")
st.caption("Ask, analyze, verify, and act across cannabis operations.")

# Sidebar
st.sidebar.header("Workspace")
persona = st.sidebar.selectbox(
    "Role",
    ["buyer", "retail_ops", "compliance", "extraction", "executive"]
)
state = st.sidebar.selectbox("State", sorted(REGULATION_LINKS.keys()))

# Chat input
prompt = st.text_area(
    "Ask anything",
    placeholder="Why is my inventory not moving?",
    height=120
)

# Run copilot
if st.button("Ask DoobieLogic", type="primary") and prompt:
    response = copilot.ask(prompt, persona=persona, state=state)
    st.session_state.chat_history.append({
        "q": prompt,
        "res": response
    })

# Display chat
for item in reversed(st.session_state.chat_history):
    res = item.get("res")
    if res is None:
        continue

    st.markdown("---")
    st.markdown(f"**You:** {item['q']}")

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
