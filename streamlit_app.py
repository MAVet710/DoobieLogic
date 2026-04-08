from __future__ import annotations

import hashlib
from dataclasses import asdict

import streamlit as st

from doobielogic.buyer_brain import render_buyer_brain_summary, summarize_buyer_opportunities
from doobielogic.copilot import DoobieCopilot
from doobielogic.department_parsers import parse_department_file
from doobielogic.department_router import detect_department_from_headers
from doobielogic.operations_engine import build_operations_outputs, render_operations_summary
from doobielogic.parser import analyze_mapped_data, basic_cannabis_mapping, load_csv_bytes, render_insight_summary
from doobielogic.regulations import REGULATION_LINKS


st.set_page_config(page_title="DoobieLogic", page_icon="🌿", layout="wide")


SESSION_DEFAULTS = {
    "chat_history": [],
    "csv_active": False,
    "uploaded_file_name": "",
    "uploaded_digest": "",
    "parsed_data": {},
    "mapped_data": {},
    "file_insights": {},
    "buyer_brain": {},
    "detected_department": "retail_ops",
    "operations_outputs": {},
}


def _init_state() -> None:
    for key, default in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _clear_file_state() -> None:
    st.session_state.csv_active = False
    st.session_state.uploaded_file_name = ""
    st.session_state.uploaded_digest = ""
    st.session_state.parsed_data = {}
    st.session_state.mapped_data = {}
    st.session_state.file_insights = {}
    st.session_state.buyer_brain = {}
    st.session_state.detected_department = "retail_ops"
    st.session_state.operations_outputs = {}


def _process_upload(uploaded, state: str) -> None:
    file_bytes = uploaded.getvalue()
    digest = hashlib.sha1(file_bytes).hexdigest()
    if digest == st.session_state.uploaded_digest:
        return

    rows = load_csv_bytes(file_bytes)
    if rows is None:
        raise ValueError("Could not parse CSV. Please upload a valid CSV file.")

    headers = list(rows[0].keys()) if rows else []
    detected = detect_department_from_headers(headers)

    st.session_state.csv_active = True
    st.session_state.uploaded_file_name = uploaded.name
    st.session_state.uploaded_digest = digest
    st.session_state.detected_department = detected

    if detected in {"retail_ops", "buyer"}:
        mapped = basic_cannabis_mapping(rows)
        st.session_state.parsed_data = {}
        st.session_state.mapped_data = mapped
        st.session_state.file_insights = analyze_mapped_data(mapped)
        st.session_state.buyer_brain = summarize_buyer_opportunities(mapped)
        st.session_state.operations_outputs = build_operations_outputs(mapped, department="retail_ops", state=state)
    else:
        parsed = parse_department_file(rows, detected)
        compact_parsed = {k: (v[:500] if isinstance(v, list) else v) for k, v in parsed.items()}
        st.session_state.parsed_data = compact_parsed
        st.session_state.mapped_data = {}
        st.session_state.file_insights = {}
        st.session_state.buyer_brain = {}
        st.session_state.operations_outputs = build_operations_outputs(compact_parsed, department=detected, state=state)


def main() -> None:
    _init_state()
    copilot = DoobieCopilot()

    st.title("🌿 DoobieLogic Copilot")
    st.caption("Department-aware cannabis operating copilot with curated learned knowledge and conservative grounded context.")

    st.sidebar.header("Workspace")
    persona = st.sidebar.selectbox("Role", ["buyer", "retail_ops", "cultivation", "extraction", "kitchen", "packaging", "compliance", "executive"])
    state = st.sidebar.selectbox("State", sorted(REGULATION_LINKS.keys()))

    st.sidebar.subheader("File Controls")
    if st.sidebar.button("Clear file"):
        _clear_file_state()
    if st.sidebar.button("Clear chat"):
        st.session_state.chat_history = []

    uploaded = st.file_uploader("Upload department CSV", type=["csv"])
    if uploaded is not None:
        try:
            _process_upload(uploaded, state)
        except Exception as exc:
            st.error(f"File processing error: {exc}")
            _clear_file_state()

    if st.session_state.csv_active:
        st.success(f"CSV active: {st.session_state.uploaded_file_name} | Detected department: {st.session_state.detected_department}")
    else:
        st.caption("No CSV active. Copilot will use built-in learned department knowledge and grounded source context.")

    copilot_tab, ops_tab = st.tabs(["Copilot", "Operations"])

    with copilot_tab:
        if st.session_state.detected_department in {"retail_ops", "buyer"} and st.session_state.file_insights:
            with st.expander("📈 File Intelligence", expanded=True):
                st.markdown(render_insight_summary(st.session_state.file_insights))
                st.markdown(render_buyer_brain_summary(st.session_state.buyer_brain))

        quick_options = {
            "cultivation": ["room performance", "yield variance", "cultivation action plan"],
            "extraction": ["yield review", "throughput review", "extraction action plan"],
            "kitchen": ["dosage control", "qc risk", "kitchen action plan"],
            "packaging": ["reconciliation risk", "packaging efficiency", "packaging action plan"],
            "compliance": ["issue concentration", "corrective action age", "compliance action plan"],
        }
        fallback_quick = ["slow movers", "reorder opportunities", "markdown candidates", "category risk"]
        quick_action = st.selectbox("Quick actions", ["None"] + quick_options.get(persona, fallback_quick), key="quick_action")

        prompt = st.text_area("Ask anything", placeholder="What should I focus on this week?", height=120, key="prompt_input")

        if st.button("Ask DoobieLogic", type="primary", key="ask_button"):
            final_prompt = prompt.strip()
            if quick_action != "None":
                final_prompt = (final_prompt + "\n\n" if final_prompt else "") + f"Quick action focus: {quick_action}."

            if not final_prompt:
                st.warning("Please enter a question or select a quick action.")
            else:
                try:
                    if st.session_state.csv_active:
                        dept = st.session_state.detected_department
                        if dept in {"retail_ops", "buyer"}:
                            response = copilot.ask_with_buyer_brain(final_prompt, mapped_data=st.session_state.mapped_data, persona=persona, state=state)
                        else:
                            response = copilot.ask_with_operations(final_prompt, department=dept, parsed_data=st.session_state.parsed_data, persona=persona, state=state)
                    else:
                        response = copilot.ask(final_prompt, persona=persona, state=state)
                    st.session_state.chat_history.append({"q": final_prompt, "res": asdict(response)})
                except Exception as exc:
                    st.error(f"Copilot error: {exc}")

        for item in reversed(st.session_state.chat_history):
            res = item.get("res") or {}
            st.markdown("---")
            st.markdown(f"**You:** {item.get('q', '')}")
            st.markdown("### 🧠 Answer")
            st.write(res.get("answer", "No answer available."))
            st.markdown("### ⚠️ Confidence")
            st.write(str(res.get("confidence", "unknown")).upper())
            st.markdown("### 🔍 Grounding")
            st.write(res.get("grounding", "No grounding data available."))
            for section, title in [("sources", "📚 Sources"), ("suggestions", "⚡ Next Moves")]:
                vals = res.get(section, []) or []
                if vals:
                    st.markdown(f"### {title}")
                    for v in vals:
                        st.write(f"- {v}")

    with ops_tab:
        st.subheader("Department Operations Output")
        try:
            if st.session_state.operations_outputs:
                st.write(render_operations_summary(st.session_state.operations_outputs, st.session_state.detected_department))
                if st.checkbox("Show raw operations payload", value=False, key="show_ops_payload"):
                    st.json(st.session_state.operations_outputs)
            else:
                st.caption("No file-derived operations output yet. Upload a CSV to run department analysis.")
        except Exception as exc:
            st.error(f"Operations rendering error: {exc}")


try:
    main()
except Exception as exc:  # global safety net against white-screen crashes
    st.error("Unexpected app error. Please copy the details below.")
    st.exception(exc)
