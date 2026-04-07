from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from doobielogic.community import CommunityAnswer, CommunityStore, VerificationReport, new_answer_id, now_iso
from doobielogic.engine import CannabisLogicEngine
from doobielogic.models import CannabisInput
from doobielogic.regulations import REGULATION_LINKS
from doobielogic.verification import verify_sources

BRAND_GREEN = "#0B5D2A"
BRAND_GOLD = "#D4A017"
LOGO_PATH = Path("assets/doobielogic_logo.png")

page_icon = str(LOGO_PATH) if LOGO_PATH.exists() else "🌿"
st.set_page_config(page_title="DoobieLogic", page_icon=page_icon, layout="wide")

st.markdown(
    f"""
    <style>
        .stApp {{
            background: linear-gradient(180deg, #F5F7F5 0%, #FFFFFF 100%);
        }}
        h1, h2, h3 {{
            color: {BRAND_GREEN};
        }}
        .stTabs [data-baseweb="tab"] {{
            color: {BRAND_GREEN};
            font-weight: 600;
        }}
        .stTabs [aria-selected="true"] {{
            border-bottom: 3px solid {BRAND_GOLD};
        }}
        .brand-chip {{
            display: inline-block;
            background: {BRAND_GOLD};
            color: {BRAND_GREEN};
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
            font-weight: 700;
            margin-bottom: 0.6rem;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

if LOGO_PATH.exists():
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(str(LOGO_PATH), width=170)
    with c2:
        st.markdown('<div class="brand-chip">DoobieLogic</div>', unsafe_allow_html=True)
        st.title("Cannabis AI Workspace")
        st.caption("Buyer KPI scoring + verified community intelligence.")
else:
    st.markdown('<div class="brand-chip">DoobieLogic</div>', unsafe_allow_html=True)
    st.title("🌿 Cannabis AI Workspace")
    st.caption("Add your provided logo file at `assets/doobielogic_logo.png` to enable full branded imagery.")

if "engine" not in st.session_state:
    st.session_state.engine = CannabisLogicEngine()
if "community_store" not in st.session_state:
    st.session_state.community_store = CommunityStore()
if "latest_output" not in st.session_state:
    st.session_state.latest_output = None

engine: CannabisLogicEngine = st.session_state.engine
community_store: CommunityStore = st.session_state.community_store

analysis_tab, community_tab = st.tabs(["Buyer Analysis", "Community Q&A"])

with analysis_tab:
    st.subheader("Buyer KPI Analysis")

    col1, col2, col3 = st.columns(3)
    with col1:
        state = st.selectbox("State", sorted(REGULATION_LINKS.keys()), index=4)
        period_start = st.date_input("Period start", value=date(2026, 1, 1))
        period_end = st.date_input("Period end", value=date(2026, 1, 31))
        total_sales_usd = st.number_input("Total sales (USD)", min_value=0.0, value=4200000.0, step=10000.0)
        transactions = st.number_input("Transactions", min_value=0, value=91000, step=100)

    with col2:
        units_sold = st.number_input("Units sold", min_value=0, value=238000, step=100)
        avg_basket_usd = st.number_input("Avg basket (USD)", min_value=0.0, value=46.15, step=0.1)
        inventory_days_on_hand = st.number_input("Inventory days on hand", min_value=0.0, value=37.0, step=1.0)
        discount_rate_pct = st.number_input("Discount rate (%)", min_value=0.0, max_value=100.0, value=12.5, step=0.5)
        price_per_gram_usd = st.number_input("Price/gram (USD)", min_value=0.0, value=6.8, step=0.1)

    with col3:
        active_retailers = st.number_input("Active retailers", min_value=0, value=1240, step=1)
        license_violations = st.number_input("License violations", min_value=0, value=1, step=1)
        flower_pct = st.slider("Flower %", 0, 100, 43)
        vape_pct = st.slider("Vape %", 0, 100, 21)
        edible_pct = st.slider("Edible %", 0, 100, 18)
        concentrate_pct = st.slider("Concentrate %", 0, 100, 11)

    other_pct = max(0, 100 - (flower_pct + vape_pct + edible_pct + concentrate_pct))
    st.write(f"Auto-calculated Other %: **{other_pct}**")

    if st.button("Run DoobieLogic Analysis", type="primary"):
        payload = CannabisInput(
            state=state,
            period_start=period_start,
            period_end=period_end,
            total_sales_usd=total_sales_usd,
            transactions=transactions,
            units_sold=units_sold,
            avg_basket_usd=avg_basket_usd,
            inventory_days_on_hand=inventory_days_on_hand,
            discount_rate_pct=discount_rate_pct,
            price_per_gram_usd=price_per_gram_usd,
            active_retailers=active_retailers,
            license_violations=license_violations,
            product_mix={
                "flower_pct": float(flower_pct),
                "vape_pct": float(vape_pct),
                "edible_pct": float(edible_pct),
                "concentrate_pct": float(concentrate_pct),
                "other_pct": float(other_pct),
            },
        )
        output = engine.analyze(payload)
        st.session_state.latest_output = output

    if st.session_state.latest_output:
        out = st.session_state.latest_output
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Score", out.score)
        k2.metric("Tier", out.tier)
        k3.metric("Compliance risk", out.compliance_risk)
        k4.metric("Inventory stress", out.inventory_stress)

        st.markdown("#### Recommendations")
        for r in out.recommendations:
            st.write(f"- {r}")

        st.markdown("#### Regulation links")
        for name, link in out.regulation_links.items():
            st.write(f"- **{name.title()}**: {link}")

with community_tab:
    st.subheader("Community Learning & Verified Answers")

    with st.form("ask_question", clear_on_submit=True):
        asked_by = st.text_input("Your name/team")
        role = st.selectbox("Role", ["buyer", "operator", "compliance", "analyst", "other"])
        q_state = st.selectbox("Question state", sorted(REGULATION_LINKS.keys()), key="q_state")
        question_text = st.text_area("Question")
        tags = st.text_input("Tags (comma separated)")
        submitted_q = st.form_submit_button("Submit question")

        if submitted_q and asked_by and len(question_text) >= 10:
            q = community_store.create_question(
                asked_by=asked_by,
                role=role,
                state=q_state,
                question_text=question_text,
                tags=[t.strip() for t in tags.split(",") if t.strip()],
            )
            st.success(f"Question submitted: {q.question_id}")

    questions = community_store.list_questions()
    st.markdown(f"### Open questions ({len(questions)})")

    for q in questions:
        with st.expander(f"[{q.state}] {q.question_text[:100]}"):
            st.write(f"**Asked by:** {q.asked_by} ({q.role})")
            st.write(f"**Tags:** {', '.join(q.tags) if q.tags else 'none'}")
            st.write(f"**Created:** {q.created_at}")

            with st.form(f"answer_{q.question_id}", clear_on_submit=True):
                responder_role = st.selectbox(
                    "Responder role",
                    ["buyer", "operator", "compliance", "analyst", "other"],
                    key=f"role_{q.question_id}",
                )
                answer_text = st.text_area("Answer", key=f"ans_{q.question_id}")
                sources = st.text_area(
                    "Sources (one URL per line; must include trusted source)",
                    key=f"src_{q.question_id}",
                )
                submitted_a = st.form_submit_button("Submit verified answer")

                if submitted_a:
                    src_list = [s.strip() for s in sources.splitlines() if s.strip()]
                    verified, trusted, untrusted = verify_sources(src_list)
                    if not verified:
                        st.error("Rejected: include at least one trusted source (.gov/.edu or approved regulator domain).")
                    elif len(answer_text.strip()) < 20:
                        st.error("Answer must be at least 20 characters.")
                    else:
                        report = VerificationReport(
                            verified=True,
                            trusted_sources=trusted,
                            untrusted_sources=untrusted,
                            checked_at=now_iso(),
                            notes="Automated source-domain verification passed. Human review recommended for policy-critical responses.",
                        )
                        answer = CommunityAnswer(
                            answer_id=new_answer_id(),
                            responder_role=responder_role,
                            answer_text=answer_text,
                            sources=src_list,
                            verification=report,
                            created_at=now_iso(),
                        )
                        community_store.add_answer(q.question_id, answer)
                        st.success("Verified answer added.")

            if q.answers:
                st.markdown("**Verified answers**")
                for a in q.answers:
                    st.write(f"- {a.answer_text}")
                    st.caption(f"Sources: {', '.join(a.sources)}")
                    st.caption(f"Trusted: {', '.join(a.verification.trusted_sources)}")
