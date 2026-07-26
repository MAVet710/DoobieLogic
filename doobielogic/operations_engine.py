from __future__ import annotations

from doobielogic.compliance_ops import build_compliance_action_plan, render_compliance_action_plan
from doobielogic.cultivation_ops import build_cultivation_action_plan, render_cultivation_action_plan
from doobielogic.department_knowledge import render_department_knowledge_summary, search_department_knowledge
from doobielogic.extraction_ops import build_extraction_action_plan, render_extraction_action_plan
from doobielogic.kitchen_ops import build_kitchen_action_plan, render_kitchen_action_plan
from doobielogic.packaging_ops import build_packaging_action_plan, render_packaging_action_plan
from doobielogic.retail_ops import build_retail_action_plan, render_retail_action_plan


def _columnar_data(parsed_data: dict | None) -> dict:
    """Accept both one-record API payloads and dashboard-style column arrays."""
    normalized: dict = {}
    for key, value in (parsed_data or {}).items():
        if value is None:
            normalized[key] = []
        elif isinstance(value, list):
            normalized[key] = value
        elif isinstance(value, (tuple, set)):
            normalized[key] = list(value)
        elif isinstance(value, dict):
            normalized[key] = value
        else:
            normalized[key] = [value]
    return normalized


def build_operations_outputs(parsed_data: dict | None, department: str, state: str | None = None) -> dict:
    dept = (department or "retail_ops").lower()
    data = _columnar_data(parsed_data)
    knowledge = search_department_knowledge(dept if dept != "buyer" else "retail_ops", " ".join(data.keys()) if data else "operational risk controls", limit=5)

    if dept in {"retail_ops", "buyer"}:
        plan = build_retail_action_plan(data)
        rendered = render_retail_action_plan(plan)
    elif dept == "cultivation":
        plan = build_cultivation_action_plan(data)
        rendered = render_cultivation_action_plan(plan)
    elif dept == "extraction":
        plan = build_extraction_action_plan(data)
        rendered = render_extraction_action_plan(plan)
    elif dept == "kitchen":
        plan = build_kitchen_action_plan(data)
        rendered = render_kitchen_action_plan(plan)
    elif dept == "packaging":
        plan = build_packaging_action_plan(data)
        rendered = render_packaging_action_plan(plan)
    elif dept == "compliance":
        plan = build_compliance_action_plan(data, state=state)
        rendered = render_compliance_action_plan(plan)
    else:  # executive or fallback
        plan = {"actions": ["Review recurring cross-functional bottlenecks and aging risk signals."]}
        rendered = "Executive action plan:\n- Focus on recurring bottlenecks, aging risks, and ownership."

    return {
        "department": dept,
        "knowledge_matches": knowledge,
        "knowledge_summary": render_department_knowledge_summary(knowledge),
        "file_signals": plan,
        "action_plan": rendered,
    }


def render_operations_summary(outputs: dict, department: str) -> str:
    return "\n\n".join(
        [
            f"Department: {department}",
            outputs.get("knowledge_summary", "No knowledge summary available."),
            "File-derived operational signals are heuristic unless explicitly marked grounded.",
            outputs.get("action_plan", "No action plan available."),
        ]
    )
