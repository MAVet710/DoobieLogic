from typing import Any

from doobielogic.buyer_brain import summarize_buyer_opportunities, render_buyer_brain_summary
from doobielogic.extraction_ops import build_extraction_action_plan, render_extraction_action_plan
from doobielogic.extraction_science_v2 import analyze_science
from doobielogic.public_knowledge_v2 import build_public_context_v2


def cross_signal(buyer: dict, extraction: dict, science: dict) -> list[str]:
    insights = []

    # Example cross logic
    if buyer.get("low_velocity", {}).get("low_velocity_count", 0) > 5 and science.get("findings"):
        insights.append("Low product velocity may be linked to extraction quality (terpene loss or harsh purge)")

    if extraction.get("risk_signals", {}).get("failed_batches", 0) > 0:
        insights.append("Failed batches may be impacting downstream retail performance and inventory gaps")

    return insights


def build_intel_v3(question: str, data: dict[str, Any], mode: str, state: str | None = None):
    buyer = summarize_buyer_opportunities(data)
    extraction = build_extraction_action_plan(data)
    science = analyze_science(data)
    public = build_public_context_v2(question, state)

    parts = []

    if mode == "buyer":
        parts.append(render_buyer_brain_summary(buyer))

    if mode == "extraction":
        parts.append(render_extraction_action_plan(extraction))
        parts.append("\n".join(science.get("findings", [])))

    cross = cross_signal(buyer, extraction, science)
    if cross:
        parts.append("Cross-functional insights:\n" + "\n".join(f"- {c}" for c in cross))

    if public.get("context"):
        parts.append("Public context available for compliance grounding")

    return {
        "answer": "\n\n".join(parts),
        "recommendations": extraction.get("actions", []) + buyer.get("markdown_candidates", {}).get("candidates", []),
        "confidence": "high",
        "cross_signals": cross,
    }
