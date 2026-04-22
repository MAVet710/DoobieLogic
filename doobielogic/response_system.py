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
        "priorities": ["yield", "stage loss", "failed batches", "throughput", "formulation / terpene context", "cost per gram / value per gram / margin"],
        "response_style": "run-performance and corrective-action brief",
        "required_sections": ["answer", "explanation", "recommendations", "risk_flags", "inefficiencies"],
        "brevity_preference": "concise",
    },
    "retail_ops": {
        "tone": "store-operations and service-level focused",
        "priorities": ["conversion", "ATV/UPT", "queue throughput", "staffing vs demand", "stockout prevention"],
        "response_style": "store floor execution brief",
        "required_sections": ["answer", "explanation", "recommendations", "risk_flags", "inefficiencies"],
        "brevity_preference": "concise",
    },
    "cultivation": {
        "tone": "production agronomy and quality-control focused",
        "priorities": ["canopy productivity", "harvest cadence", "quality pass rate", "room-level variance", "labor bottlenecks"],
        "response_style": "grow operations stabilization brief",
        "required_sections": ["answer", "explanation", "recommendations", "risk_flags", "inefficiencies"],
        "brevity_preference": "concise",
    },
    "kitchen": {
        "tone": "batch-control and food-safety disciplined",
        "priorities": ["potency consistency", "batch yield", "sanitation/changeover controls", "traceability", "packaging handoff timing"],
        "response_style": "kitchen process-control brief",
        "required_sections": ["answer", "explanation", "recommendations", "risk_flags", "inefficiencies"],
        "brevity_preference": "concise",
    },
    "packaging": {
        "tone": "line-balance and unit-quality focused",
        "priorities": ["label accuracy", "first-pass yield", "reconciliation", "throughput bottlenecks", "release readiness"],
        "response_style": "packaging line-control brief",
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


@dataclass
class AnswerPlan:
    conclusion: str
    supporting_points: list[str]
    next_step: str
    response_shape: str


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


def _build_citation_pool(evidence: list[dict[str, Any]] | None, limit: int = 4) -> list[str]:
    refs: list[str] = []
    for item in evidence or []:
        label = str(item.get("citation") or "").strip()
        if label and label not in refs:
            refs.append(label)
        if len(refs) >= limit:
            break
    return refs


def _infer_response_shape(question: str, mode: str, risk_flags: list[str]) -> str:
    q = (question or "").lower()
    if any(token in q for token in ("checklist", "sop", "plan", "steps", "playbook")):
        return "step_by_step"
    if any(token in q for token in ("compare", "vs", "tradeoff")):
        return "comparison"
    if any(token in q for token in ("risk", "compliance", "audit")) or mode == "compliance" or len(risk_flags) >= 3:
        return "risk_summary"
    if any(token in q for token in ("report", "summary", "brief")):
        return "structured_report"
    return "natural_prose"


def _plan_answer(
    *,
    question: str,
    mode: str,
    quick_answer: str,
    recommendations: list[str],
    risk_flags: list[str],
    inefficiencies: list[str],
    explanation_context: str,
) -> AnswerPlan:
    placeholder_markers = ("brief ready", "brief generated", "analysis prepared")
    normalized_answer = quick_answer.strip()
    if any(marker in normalized_answer.lower() for marker in placeholder_markers):
        if risk_flags:
            normalized_answer = f"Your top priority is to address {risk_flags[0].lower()} before scaling optimization work."
        elif inefficiencies:
            normalized_answer = f"The key fix is to remove this bottleneck first: {inefficiencies[0]}"
        elif recommendations:
            normalized_answer = recommendations[0]

    support = []
    if risk_flags:
        support.append(f"Main risk signal: {risk_flags[0]}.")
    if inefficiencies:
        support.append(f"Efficiency drag to fix: {inefficiencies[0]}.")
    if explanation_context:
        support.append(explanation_context.split("\n")[0].strip())
    if not support:
        support.append("Current structured context is limited, so this answer stays conservative.")

    next_step = recommendations[0] if recommendations else "Confirm the top bottleneck owner and run a same-week corrective action check."
    shape = _infer_response_shape(question, mode, risk_flags)
    return AnswerPlan(conclusion=normalized_answer, supporting_points=support[:3], next_step=next_step, response_shape=shape)


def _render_explanation(plan: AnswerPlan, citations: list[str], recommendations: list[str]) -> str:
    citation_text = " " + " ".join(citations) if citations else ""
    if plan.response_shape in {"step_by_step", "structured_report"}:
        steps = [f"{idx + 1}) {point}" for idx, point in enumerate(plan.supporting_points)]
        steps.append(f"{len(steps) + 1}) Next step: {plan.next_step}")
        return "\n".join(steps) + citation_text

    if plan.response_shape == "comparison":
        left = plan.supporting_points[0] if plan.supporting_points else "Current-state evidence is strongest."
        right = plan.supporting_points[1] if len(plan.supporting_points) > 1 else "Alternative path has weaker evidence right now."
        return f"Best path: {left} Alternative view: {right} Next step: {plan.next_step}.{citation_text}"

    if plan.response_shape == "risk_summary":
        detail = " ".join(plan.supporting_points)
        return f"Risk view: {detail} Practical next step: {plan.next_step}.{citation_text}"

    detail = " ".join(plan.supporting_points)
    rec = recommendations[0] if recommendations else plan.next_step
    return f"{detail} The most useful move now is: {rec}.{citation_text}"


def _build_response(
    mode: str,
    quick_answer: str,
    explanation_context: str,
    recommendations: list[str] | None,
    risk_flags: list[str] | None,
    inefficiencies: list[str] | None,
    confidence: str,
    sources: list[str] | None,
    question: str = "",
    evidence: list[dict[str, Any]] | None = None,
) -> StructuredResponse:
    clean_risks = _clean_list(risk_flags)
    clean_inefficiencies = _clean_list(inefficiencies)
    clean_recommendations = _clean_list(recommendations)
    citation_pool = _build_citation_pool(evidence)
    plan = _plan_answer(
        question=question,
        mode=mode,
        quick_answer=quick_answer,
        recommendations=clean_recommendations,
        risk_flags=clean_risks,
        inefficiencies=clean_inefficiencies,
        explanation_context=explanation_context.strip(),
    )
    explanation = _render_explanation(plan, citation_pool, clean_recommendations)
    source_refs = _clean_list((sources or []) + citation_pool)

    return StructuredResponse(
        answer=plan.conclusion,
        explanation=explanation,
        recommendations=clean_recommendations,
        confidence=confidence,
        sources=source_refs,
        mode=mode,
        risk_flags=clean_risks,
        inefficiencies=clean_inefficiencies,
    )


def build_buyer_response(**kwargs: Any) -> StructuredResponse:
    return _build_response("buyer", **kwargs)


def build_inventory_response(**kwargs: Any) -> StructuredResponse:
    return _build_response("inventory", **kwargs)


def build_extraction_response(**kwargs: Any) -> StructuredResponse:
    return _build_response("extraction", **kwargs)


def build_retail_ops_response(**kwargs: Any) -> StructuredResponse:
    return _build_response("retail_ops", **kwargs)


def build_cultivation_response(**kwargs: Any) -> StructuredResponse:
    return _build_response("cultivation", **kwargs)


def build_kitchen_response(**kwargs: Any) -> StructuredResponse:
    return _build_response("kitchen", **kwargs)


def build_packaging_response(**kwargs: Any) -> StructuredResponse:
    return _build_response("packaging", **kwargs)


def build_ops_response(**kwargs: Any) -> StructuredResponse:
    return _build_response("ops", **kwargs)


def build_copilot_response(**kwargs: Any) -> StructuredResponse:
    return _build_response("copilot", **kwargs)


def build_compliance_response(**kwargs: Any) -> StructuredResponse:
    return _build_response("compliance", **kwargs)


def build_executive_response(**kwargs: Any) -> StructuredResponse:
    return _build_response("executive", **kwargs)


RESPONSE_BUILDERS = {
    "buyer": build_buyer_response,
    "inventory": build_inventory_response,
    "extraction": build_extraction_response,
    "retail_ops": build_retail_ops_response,
    "cultivation": build_cultivation_response,
    "kitchen": build_kitchen_response,
    "packaging": build_packaging_response,
    "ops": build_ops_response,
    "copilot": build_copilot_response,
    "compliance": build_compliance_response,
    "executive": build_executive_response,
}
