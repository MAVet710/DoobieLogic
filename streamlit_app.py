from __future__ import annotations

from dataclasses import asdict

import streamlit as st

from doobielogic.regulations import REGULATION_LINKS

st.set_page_config(page_title="DoobieLogic", page_icon="🌿", layout="wide")


def _init_state() -> None:
    defaults = {
        "chat_history": [],
        "csv_active": False,
        "uploaded_file_name": "",
        "uploaded_token": "",
        "detected_department": "retail_ops",
        "mapped_data": {},
        "parsed_data": {},
        "file_insights": {},
        "buyer_brain": {},
        "operations_outputs": {},
        "last_error": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _clear_file_state() -> None:
    st.session_state.csv_active = False
    st.session_state.uploaded_file_name = ""
    st.session_state.uploaded_token = ""
    st.session_state.detected_department = "retail_ops"
    st.session_state.mapped_data = {}
    st.session_state.parsed_data = {}
    st.session_state.file_insights = {}
    st.session_state.buyer_brain = {}
    st.session_state.operations_outputs = {}


def _process_upload(uploaded_file, state: str) -> None:
    from doobielogic.buyer_brain import summarize_buyer_opportunities
    from doobielogic.department_parsers import parse_department_file
    from doobielogic.department_router import detect_department_from_headers
    from doobielogic.operations_engine import build_operations_outputs
    from doobielogic.parser import analyze_mapped_data, basic_cannabis_mapping, load_csv_bytes

    rows = load_csv_bytes(uploaded_file.getvalue())
    if not rows:
        raise ValueError("CSV appears empty or invalid.")

    detected = detect_department_from_headers(list(rows[0].keys()))
    st.session_state.detected_department = detected
    st.session_state.uploaded_file_name = uploaded_file.name
    st.session_state.csv_active = True

    if detected in {"retail_ops", "buyer"}:
        mapped = basic_cannabis_mapping(rows)
        st.session_state.mapped_data = mapped
        st.session_state.parsed_data = {}
        st.session_state.file_insights = analyze_mapped_data(mapped)
        st.session_state.buyer_brain = summarize_buyer_opportunities(mapped)
        st.session_state.operations_outputs = build_operations_outputs(mapped, "retail_ops", state=state)
    else:
        parsed = parse_department_file(rows, detected)
        compact = {k: (v[:300] if isinstance(v, list) else v) for k, v in parsed.items()}
        st.session_state.parsed_data = compact
        st.session_state.mapped_data = {}
        st.session_state.file_insights = {}
        st.session_state.buyer_brain = {}
        st.session_state.operations_outputs = build_operations_outputs(compact, detected, state=state)


def _ask(question: str, persona: str, state: str) -> dict:
    from doobielogic.copilot import DoobieCopilot

    cp = DoobieCopilot()
    if st.session_state.csv_active:
        dept = st.session_state.detected_department
        if dept in {"retail_ops", "buyer"}:
            return asdict(cp.ask_with_buyer_brain(question, st.session_state.mapped_data, persona=persona, state=state))
        return asdict(cp.ask_with_operations(question, dept, st.session_state.parsed_data, persona=persona, state=state))
    return asdict(cp.ask(question, persona=persona, state=state))


def main() -> None:
    _init_state()

    st.title("🌿 DoobieLogic Copilot")

    st.sidebar.header("Workspace")
    persona = st.sidebar.selectbox("Role", ["buyer", "retail_ops", "cultivation", "extraction", "kitchen", "packaging", "compliance", "executive"], key="role_select")
    state = st.sidebar.selectbox("State", sorted(REGULATION_LINKS.keys()), key="state_select")

    st.sidebar.subheader("File Controls")
    if st.sidebar.button("Clear file", key="clear_file"):
        _clear_file_state()
    if st.sidebar.button("Clear chat", key="clear_chat"):
        st.session_state.chat_history = []

    uploaded = st.file_uploader("Upload department CSV", type=["csv"], key="uploader")
    if uploaded is not None:
        token = f"{uploaded.name}:{getattr(uploaded, 'size', 0)}"
        if token != st.session_state.uploaded_token and st.button("Process uploaded file", key="process_file"):
            try:
                _process_upload(uploaded, state)
                st.session_state.uploaded_token = token
            except Exception as exc:
                st.session_state.last_error = str(exc)
                st.error(f"Upload processing error: {exc}")

    if st.session_state.csv_active:
        st.success(f"Active file: {st.session_state.uploaded_file_name} | Department: {st.session_state.detected_department}")

    prompt = st.text_area("Ask anything", key="ask_text", height=120)
    if st.button("Ask DoobieLogic", key="ask_btn"):
        if not prompt.strip():
            st.warning("Type a prompt first.")
        else:
            try:
                response = _ask(prompt.strip(), persona, state)
                st.session_state.chat_history.append({"q": prompt.strip(), "res": response})
                st.session_state.chat_history = st.session_state.chat_history[-30:]
            except Exception as exc:
                st.session_state.last_error = str(exc)
                st.error(f"Ask failed: {exc}")

    if st.session_state.last_error:
        with st.expander("Last error details"):
            st.code(st.session_state.last_error)

    for item in reversed(st.session_state.chat_history[-10:]):
        st.markdown("---")
        st.markdown(f"**You:** {item['q']}")
        res = item.get("res", {})
        st.write(res.get("answer", "No answer."))
        st.caption(f"confidence={res.get('confidence', 'unknown')} | grounding={res.get('grounding', 'n/a')}")

    st.subheader("Operations Output")
    if st.session_state.operations_outputs:
        st.json(st.session_state.operations_outputs)


try:
    main()
except Exception as exc:
    st.error("Unexpected app error.")
    st.exception(exc)
