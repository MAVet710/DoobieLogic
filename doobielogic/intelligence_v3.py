from typing import Any

from doobielogic.buyer_brain import render_buyer_brain_summary, summarize_buyer_opportunities
from doobielogic.cannabis_intelligence import build_ai_input, format_doobie_response
from doobielogic.extraction_ops import build_extraction_action_plan, render_extraction_action_plan
from doobielogic.extraction_science_v2 import analyze_science
from doobielogic.public_knowledge_v2 import build_public_context_v2


def cross_signal(buyer: dict, extraction: dict, science: dict) -> list[str]:
    insights = []

    if buyer.get("low_velocity", {}).get("low_velocity_count", 0) > 5 and science.get("findings"):
        insights.append("Low product velocity may be linked to extraction quality (terpene loss or harsh purge).")

    if extraction.get("risk_signals", {}).get("failed_batches", 0) > 0:
        insights.append("Failed batches may be impacting downstream retail performance and inventory gaps.")

    return insights


def _compose_reasoning(ai_input: dict[str, Any], mode: str, buyer: dict, extraction: dict, science: dict, public: dict) -> tuple[str, str, list[str], list[str], list[str]]:
    context = ai_input["structured_context"]
    parts: list[str] = []
    recs: list[str] = []
    inefficiencies: list[str] = []

    if mode == "buyer":
        parts.append(render_buyer_brain_summary(buyer))
        recs.extend(buyer.get("markdown_candidates", {}).get("candidates", []))
        doh = context.get("kpis", {}).get("days_on_hand")
        if isinstance(doh, (float, int)) and doh > 75:
            inefficiencies.append("Overstocked inventory is tying up working capital.")

    if mode == "extraction":
        parts.append(render_extraction_action_plan(extraction))
        parts.append("\n".join(science.get("findings", [])))
        recs.extend(extraction.get("actions", []))
        run_yield = context.get("kpis", {}).get("yield_percent")
        if isinstance(run_yield, (float, int)) and run_yield < 8:
            inefficiencies.append("Run yield is below expected floor for most commercial extraction programs.")

    cross = cross_signal(buyer, extraction, science)
    if cross:
        parts.append("Cross-functional insights:\n" + "\n".join(f"- {c}" for c in cross))

    if public.get("context"):
        parts.append("Public context available for compliance grounding.")

    rules = context.get("relevant_rules", [])
    if rules:
        parts.append("Structured rule set applied: " + ", ".join(rules))

    explanation = "\n\n".join(parts).strip() or "No data-specific explanation available."
    answer = (parts[0].split("\n")[0] if parts else "No immediate conclusion from provided data.").strip()
    recommendation = recs[:5]
    return answer, explanation, recommendation, context.get("risk_flags", []), inefficiencies


def build_intel_v3(question: str, data: dict[str, Any], mode: str, state: str | None = None):
    buyer = summarize_buyer_opportunities(data)
    extraction = build_extraction_action_plan(data)
    science = analyze_science(data)
    public = build_public_context_v2(question, state)

    ai_input = build_ai_input(question=question, data=data, mode=mode if mode in {"buyer", "inventory", "extraction", "ops"} else "ops", state=state)

    answer, explanation, recommendation, risk_flags, inefficiencies = _compose_reasoning(
        ai_input=ai_input,
        mode=mode,
        buyer=buyer,
        extraction=extraction,
        science=science,
        public=public,
    )

    formatted = format_doobie_response(
        answer=answer,
        explanation=explanation,
        recommendations=recommendation,
        confidence="high",
        sources=public.get("sources", []),
        mode=ai_input["mode"],
    )

    return {
        **formatted,
        "cross_signals": cross_signal(buyer, extraction, science),
        "risk_flags": risk_flags,
        "inefficiencies": inefficiencies,
        "ai_input": ai_input,
    }
