from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

ModeName = str

RESPONSE_MODE_CONFIG: dict[ModeName, dict[str, Any]] = {
    "buyer": {
        "tone": "commercial, direct, margin-aware",
        "priorities": ["assortment gaps", "dead inventory", "velocity", "reorder pressure", "margin-aware action"],
        "response_style": "action brief with category and SKU pressure callouts",
        "required_sections": ["answer", "explanation", "recommendations", "risk_flags", "inefficiencies"],
        "brevity_preference": "concise",
    },
    "inventory": {
        "tone": "tactical and immediate",
        "priorities": ["low stock", "overstock", "DOH imbalance", "immediate tactical next steps"],
        "response_style": "inventory triage brief",
        "required_sections": ["answer", "explanation", "recommendations", "risk_flags", "inefficiencies"],
        "brevity_preference": "concise",
    },
    "extraction": {
        "tone": "technical and production-focused",
        "priorities": [
            "yield",
            "stage loss",
            "failed batches",
            "throughput",
            "formulation / terpene context",
            "cost per gram / value per gram / margin",
        ],
        "response_style": "run-performance and corrective-action brief",
        "required_sections": ["answer", "explanation", "recommendations", "risk_flags", "inefficiencies"],
        "brevity_preference": "concise",
    },
    "ops": {
        "tone": "execution-focused and accountable",
        "priorities": ["bottlenecks", "recurring risks", "ownership", "execution"],
        "response_style": "owner-ready operational digest",
        "required_sections": ["answer", "explanation", "recommendations", "risk_flags", "inefficiencies"],
        "brevity_preference": "concise",
    },
    "copilot": {
        "tone": "helpful and direct",
        "priorities": ["direct answer first", "explanation second", "practical next step"],
        "response_style": "rapid answer + operational next action",
        "required_sections": ["answer", "explanation", "recommendations", "risk_flags", "inefficiencies"],
        "brevity_preference": "brief",
    },
    "compliance": {
        "tone": "conservative and traceability-first",
        "priorities": ["conservative framing", "traceability", "issue recurrence", "verification against guidance"],
        "response_style": "risk-first compliance memo",
        "required_sections": ["answer", "explanation", "recommendations", "risk_flags", "inefficiencies"],
        "brevity_preference": "concise",
    },
    "executive": {
        "tone": "strategic and decision-ready",
        "priorities": ["summary", "cross-functional issues", "decision-ready next actions"],
        "response_style": "executive summary with prioritized actions",
        "required_sections": ["answer", "explanation", "recommendations", "risk_flags", "inefficiencies"],
        "brevity_preference": "brief",
    },
}


@dataclass
class StructuredResponse:
    answer: str
    explanation: str
    recommendations: list[str]
    confidence: str
    sources: list[str]
    mode: str
    risk_flags: list[str]
    inefficiencies: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def infer_confidence(
    has_structured_data: bool,
    has_grounding: bool,
    has_relevant_rules: bool,
    has_unmapped_outputs: bool = False,
    weak_context: bool = False,
) -> str:
    if weak_context or has_unmapped_outputs:
        return "low"
    if has_structured_data and has_grounding and has_relevant_rules:
        return "high"
    if has_structured_data or (has_grounding and has_relevant_rules):
        return "medium"
    return "low"


def _clean_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    cleaned: list[str] = []
    for value in values:
        safe = str(value).strip()
        if safe and safe not in cleaned:
            cleaned.append(safe)
    return cleaned


def _format_explanation(mode: str, explanation_context: str, risk_flags: list[str], inefficiencies: list[str]) -> str:
    config = RESPONSE_MODE_CONFIG.get(mode, RESPONSE_MODE_CONFIG["copilot"])
    priorities = ", ".join(config["priorities"])
    risk_text = ", ".join(risk_flags) if risk_flags else "none identified from current structured context"
    inefficiency_text = ", ".join(inefficiencies) if inefficiencies else "none identified"
    return (
        f"Mode focus ({mode}): {priorities}.\n"
        f"Operational context: {explanation_context}\n"
        f"Risk flags: {risk_text}.\n"
        f"Inefficiencies: {inefficiency_text}."
    )


def _build_response(
    mode: str,
    quick_answer: str,
    explanation_context: str,
    recommendations: list[str] | None,
    risk_flags: list[str] | None,
    inefficiencies: list[str] | None,
    confidence: str,
    sources: list[str] | None,
) -> StructuredResponse:
    clean_risks = _clean_list(risk_flags)
    clean_inefficiencies = _clean_list(inefficiencies)
    return StructuredResponse(
        answer=quick_answer.strip(),
        explanation=_format_explanation(mode, explanation_context.strip(), clean_risks, clean_inefficiencies),
        recommendations=_clean_list(recommendations),
        confidence=confidence,
        sources=_clean_list(sources),
        mode=mode,
        risk_flags=clean_risks,
        inefficiencies=clean_inefficiencies,
    )


def build_buyer_response(
    quick_answer: str,
    explanation_context: str,
    recommendations: list[str] | None,
    risk_flags: list[str] | None,
    inefficiencies: list[str] | None,
    confidence: str,
    sources: list[str] | None,
) -> StructuredResponse:
    return _build_response("buyer", quick_answer, explanation_context, recommendations, risk_flags, inefficiencies, confidence, sources)


def build_inventory_response(
    quick_answer: str,
    explanation_context: str,
    recommendations: list[str] | None,
    risk_flags: list[str] | None,
    inefficiencies: list[str] | None,
    confidence: str,
    sources: list[str] | None,
) -> StructuredResponse:
    return _build_response("inventory", quick_answer, explanation_context, recommendations, risk_flags, inefficiencies, confidence, sources)


def build_extraction_response(
    quick_answer: str,
    explanation_context: str,
    recommendations: list[str] | None,
    risk_flags: list[str] | None,
    inefficiencies: list[str] | None,
    confidence: str,
    sources: list[str] | None,
) -> StructuredResponse:
    return _build_response("extraction", quick_answer, explanation_context, recommendations, risk_flags, inefficiencies, confidence, sources)


def build_ops_response(
    quick_answer: str,
    explanation_context: str,
    recommendations: list[str] | None,
    risk_flags: list[str] | None,
    inefficiencies: list[str] | None,
    confidence: str,
    sources: list[str] | None,
) -> StructuredResponse:
    return _build_response("ops", quick_answer, explanation_context, recommendations, risk_flags, inefficiencies, confidence, sources)


def build_copilot_response(
    quick_answer: str,
    explanation_context: str,
    recommendations: list[str] | None,
    risk_flags: list[str] | None,
    inefficiencies: list[str] | None,
    confidence: str,
    sources: list[str] | None,
) -> StructuredResponse:
    return _build_response("copilot", quick_answer, explanation_context, recommendations, risk_flags, inefficiencies, confidence, sources)


def build_compliance_response(
    quick_answer: str,
    explanation_context: str,
    recommendations: list[str] | None,
    risk_flags: list[str] | None,
    inefficiencies: list[str] | None,
    confidence: str,
    sources: list[str] | None,
) -> StructuredResponse:
    return _build_response("compliance", quick_answer, explanation_context, recommendations, risk_flags, inefficiencies, confidence, sources)


def build_executive_response(
    quick_answer: str,
    explanation_context: str,
    recommendations: list[str] | None,
    risk_flags: list[str] | None,
    inefficiencies: list[str] | None,
    confidence: str,
    sources: list[str] | None,
) -> StructuredResponse:
    return _build_response("executive", quick_answer, explanation_context, recommendations, risk_flags, inefficiencies, confidence, sources)


RESPONSE_BUILDERS = {
    "buyer": build_buyer_response,
    "inventory": build_inventory_response,
    "extraction": build_extraction_response,
    "ops": build_ops_response,
    "copilot": build_copilot_response,
    "compliance": build_compliance_response,
    "executive": build_executive_response,
}
