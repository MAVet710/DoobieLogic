from typing import Any
from doobielogic.buyer_brain import summarize_buyer_opportunities, render_buyer_brain_summary
from doobielogic.extraction_ops import build_extraction_action_plan, render_extraction_action_plan
from doobielogic.extraction_science_v2 import analyze_science
from doobielogic.public_knowledge_v2 import build_public_context_v2


def build_intel(question: str, data: dict[str, Any], mode: str, state: str | None = None):
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

    if public.get("context"):
        parts.append("Public context available")

    return {
        "answer": "\n\n".join(parts),
        "recommendations": extraction.get("actions", []) + buyer.get("markdown_candidates", {}).get("candidates", []),
        "confidence": "high"
    }
