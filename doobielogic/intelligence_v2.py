from __future__ import annotations

from typing import Any

from doobielogic.buyer_brain import render_buyer_brain_summary, summarize_buyer_opportunities
from doobielogic.extraction_ops import build_extraction_action_plan, render_extraction_action_plan
from doobielogic.extraction_science_v2 import build_extraction_science_summary, render_extraction_science_summary
from doobielogic.parser import analyze_mapped_data, render_insight_summary
from doobielogic.public_knowledge_v2 import build_public_context_v2


ROLE_HINTS: dict[str, str] = {
    "buyer": "Prioritize assortment, velocity, turns, margin pressure, and reorder risk.",
    "retail_ops": "Prioritize execution friction, throughput, conversion, and category coverage.",
    "extraction": "Prioritize process conditions, release readiness, terpene preservation, purge sufficiency, and chemistry-aware interventions.",
    "compliance": "Prioritize regulator-backed context, release blockers, tracking obligations, and corrective action framing.",
    "executive": "Prioritize high-signal bottlenecks, recurring operational risks, and decision-ready actions.",
}


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        if v and v not in seen:
            out.append(v)
            seen.add(v)
    return out



def build_unified_intelligence(
    *,
    question: str,
    mapped_data: dict[str, Any] | None = None,
    persona: str = "buyer",
    state: str | None = None,
) -> dict[str, Any]:
    safe_persona = persona if persona in ROLE_HINTS else "buyer"
    mapped = mapped_data or {}

    file_insights = analyze_mapped_data(mapped) if mapped else {}
    buyer_signals = summarize_buyer_opportunities(mapped) if mapped else {}
    extraction_ops = build_extraction_action_plan(mapped) if mapped and safe_persona in {"extraction", "executive", "compliance"} else {}
    extraction_science = build_extraction_science_summary(mapped) if mapped and safe_persona in {"extraction", "executive", "compliance"} else {}
    public_context = build_public_context_v2(question=question, state=state)

    recommendations: list[str] = []
    if buyer_signals:
        recommendations.extend((buyer_signals.get("markdown_candidates", {}) or {}).get("candidates", [])[:3])
        recommendations.extend((buyer_signals.get("low_velocity", {}) or {}).get("low_velocity_products", [])[:3])
    if extraction_science:
        recommendations.extend(extraction_science.get("top_recommendations", [])[:5])
    if extraction_ops:
        recommendations.extend(extraction_ops.get("actions", [])[:5])

    answer_sections = [f"Role lens: {ROLE_HINTS[safe_persona]}"]
    if file_insights:
        answer_sections.append("File intelligence:\n" + render_insight_summary(file_insights))
    if buyer_signals and safe_persona in {"buyer", "retail_ops", "executive"}:
        answer_sections.append(render_buyer_brain_summary(buyer_signals))
    if extraction_ops and safe_persona in {"extraction", "executive", "compliance"}:
        answer_sections.append(render_extraction_action_plan(extraction_ops))
    if extraction_science and safe_persona in {"extraction", "executive", "compliance"}:
        answer_sections.append(render_extraction_science_summary(extraction_science))
    if public_context:
        lines = [f"- {row['title']}: {row['summary']}" for row in public_context.get("context", [])[:4]]
        answer_sections.append("Public knowledge context:\n" + ("\n".join(lines) if lines else "No public context matches."))

    confidence_parts = [public_context.get("confidence", "low")]
    if extraction_science:
        confidence_parts.append(extraction_science.get("confidence", "low"))
    confidence = "high" if "high" in confidence_parts else "medium" if "medium" in confidence_parts else "low"

    return {
        "persona": safe_persona,
        "state": state.upper() if isinstance(state, str) else None,
        "answer": "\n\n".join(section for section in answer_sections if section),
        "buyer_signals": buyer_signals,
        "extraction_ops": extraction_ops,
        "extraction_science": extraction_science,
        "file_insights": file_insights,
        "public_context": public_context,
        "sources": _dedupe(public_context.get("sources", [])),
        "confidence": confidence,
        "recommendations": _dedupe([r for r in recommendations if isinstance(r, str)])[:8],
        "grounding": "Unified buyer + extraction + public knowledge intelligence layer",
    }
