from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from doobielogic.department_knowledge import search_department_knowledge
from doobielogic.parser import analyze_mapped_data, render_insight_summary
from doobielogic.sourcepack import build_grounded_summary

INTEL_DIR = Path(__file__).resolve().parent.parent / "intel"
INTEL_FILES = {
    "extraction": "extraction_intel.json",
    "buyer": "buyer_intel.json",
    "compliance": "compliance_intel.json",
    "taxonomy": "product_taxonomy.json",
    "financial": "financial_intel.json",
}

# TODO: Add vector embedding index over intel modules for semantic retrieval.
# TODO: Add model fine-tuning hooks that learn weighting of rules over time.
# TODO: Add feedback-learning loop to reinforce high-quality recommendations.
# TODO: Add persistent storage backend when module versions need environment-specific overrides.


MODE_TO_INTEL = {
    "buyer": {"buyer", "financial", "taxonomy", "compliance"},
    "inventory": {"buyer", "financial", "taxonomy"},
    "extraction": {"extraction", "financial", "taxonomy", "compliance"},
    "ops": {"buyer", "extraction", "financial", "compliance", "taxonomy"},
}

DEPARTMENT_FOR_MODE = {
    "buyer": "buyer",
    "inventory": "retail_ops",
    "extraction": "extraction",
    "ops": "executive",
}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _avg(items: list[float]) -> float | None:
    return sum(items) / len(items) if items else None


def load_intel_modules(selected: set[str] | None = None) -> dict[str, Any]:
    wanted = selected or set(INTEL_FILES.keys())
    modules: dict[str, Any] = {}
    for key, filename in INTEL_FILES.items():
        if key not in wanted:
            continue
        path = INTEL_DIR / filename
        with path.open("r", encoding="utf-8") as f:
            modules[key] = json.load(f)
    return modules


def _extract_kpis(data: dict[str, Any], mode: str) -> dict[str, Any]:
    doh = _safe_float(data.get("days_on_hand") or data.get("doh"))
    velocity = _safe_float(data.get("velocity") or data.get("sales_velocity"))
    sell_through = _safe_float(data.get("sell_through_rate") or data.get("sell_through"))
    input_g = _safe_float(data.get("input_grams") or data.get("input_mass_g"))
    output_g = _safe_float(data.get("output_grams") or data.get("output_mass_g"))
    yield_percent = _safe_float(data.get("yield_percent") or data.get("yield_pct"))

    if yield_percent is None and input_g and output_g:
        yield_percent = (output_g / input_g) * 100

    inventory_rows = data.get("inventory") if isinstance(data.get("inventory"), list) else []
    if doh is None:
        doh = _avg([x for x in (_safe_float(row.get("days_on_hand")) for row in inventory_rows if isinstance(row, dict)) if x is not None])
    if velocity is None:
        velocity = _avg([x for x in (_safe_float(row.get("velocity")) for row in inventory_rows if isinstance(row, dict)) if x is not None])
    if sell_through is None:
        sell_through = _avg([x for x in (_safe_float(row.get("sell_through_rate")) for row in inventory_rows if isinstance(row, dict)) if x is not None])

    return {
        "mode": mode,
        "days_on_hand": doh,
        "velocity": velocity,
        "sell_through_rate": sell_through,
        "yield_percent": yield_percent,
        "failed_batches": int(data.get("failed_batches") or 0),
    }


def _relevant_rules(mode: str, modules: dict[str, Any]) -> list[str]:
    rules: list[str] = []
    buyer_rules = modules.get("buyer", {}).get("inventory_logic", {}).get("rules", [])
    rules.extend([str(rule.get("id")) for rule in buyer_rules if isinstance(rule, dict)])

    financial_rules = modules.get("financial", {}).get("yield_to_profit_relationships", [])
    rules.extend([str(rule.get("id")) for rule in financial_rules if isinstance(rule, dict)])

    compliance_rules = modules.get("compliance", {}).get("high_level_rules", [])
    rules.extend([str(rule.get("id")) for rule in compliance_rules if isinstance(rule, dict)])

    if mode == "inventory":
        return [rule for rule in rules if rule.startswith("buyer_")]
    if mode == "buyer":
        return [rule for rule in rules if rule.startswith("buyer_") or rule.startswith("high_yield") or rule.startswith("low_yield")]
    if mode == "extraction":
        return [rule for rule in rules if "yield" in rule or "traceability" in rule or "stage_" in rule]
    return rules


def _risk_flags(kpis: dict[str, Any], mode: str) -> list[str]:
    flags: list[str] = []
    doh = kpis.get("days_on_hand")
    sell_through = kpis.get("sell_through_rate")
    run_yield = kpis.get("yield_percent")

    if mode in {"buyer", "inventory", "ops"}:
        if isinstance(doh, (float, int)) and doh < 14:
            flags.append("Low DOH indicates restock risk.")
        if isinstance(doh, (float, int)) and doh > 75:
            flags.append("High DOH indicates dead inventory risk.")
        if isinstance(sell_through, (float, int)) and sell_through < 0.30:
            flags.append("Low sell-through indicates product mix or pricing friction.")

    if mode in {"extraction", "ops"}:
        if isinstance(run_yield, (float, int)) and run_yield < 8:
            flags.append("Low extraction yield suggests process inefficiency or weak input quality.")
        if kpis.get("failed_batches", 0) > 0:
            flags.append("Failed batches detected; review SOP compliance and QA gates.")

    return flags


def build_doobie_context(
    data: dict[str, Any] | None,
    mode: str,
    question: str | None = None,
    state: str | None = None,
) -> dict[str, Any]:
    """Build structured context used by copilot and intelligence layers.

    `question` and `state` are optional metadata inputs for lightweight context
    enrichment (department/source retrieval and return payload metadata), while
    preserving backwards compatibility with existing `build_doobie_context(data, mode)` calls.
    """
    payload = data or {}
    normalized_question = (question or "").strip()
    safe_mode = mode if mode in MODE_TO_INTEL else "ops"
    modules = load_intel_modules(MODE_TO_INTEL[safe_mode])
    kpis = _extract_kpis(payload, safe_mode)
    file_insights = analyze_mapped_data(payload) if payload else {}
    dept = DEPARTMENT_FOR_MODE[safe_mode]
    department_knowledge = search_department_knowledge(dept, normalized_question or safe_mode, limit=5)
    source_context = build_grounded_summary(question=normalized_question or safe_mode, state=state, module="operations")

    context = {
        "mode": safe_mode,
        "question": normalized_question or None,
        "state": state,
        "kpis": kpis,
        "file_insights": {
            "raw": file_insights,
            "summary": render_insight_summary(file_insights) if file_insights else "No file insights available.",
        },
        "risk_flags": _risk_flags(kpis, safe_mode),
        "relevant_rules": _relevant_rules(safe_mode, modules),
        "department_knowledge": department_knowledge,
        "source_context": source_context,
        "intel_modules": modules,
        # Backward-compatible aliases for existing downstream callers:
        "inventory_summary": {
            "days_on_hand": kpis.get("days_on_hand"),
            "velocity": kpis.get("velocity"),
            "sell_through_rate": kpis.get("sell_through_rate"),
        },
        "extraction_summary": {
            "yield_percent": kpis.get("yield_percent"),
            "failed_batches": kpis.get("failed_batches"),
        },
    }
    return context


def build_ai_input(question: str, data: dict[str, Any] | None, mode: str, state: str | None = None) -> dict[str, Any]:
    context = build_doobie_context(data=data, mode=mode, question=question, state=state)
    return {
        "question": question,
        "state": state,
        "mode": context["mode"],
        "structured_context": {
            "kpis": context["kpis"],
            "file_insights": context["file_insights"],
            "risk_flags": context["risk_flags"],
            "relevant_rules": context["relevant_rules"],
            "department_knowledge": context["department_knowledge"],
            "source_context": context["source_context"],
        },
        "intel_modules": context["intel_modules"],
    }


def format_doobie_response(answer: str, explanation: str, recommendations: list[str], confidence: str, sources: list[str], mode: str) -> dict[str, Any]:
    return {
        "answer": answer,
        "explanation": explanation,
        "recommendations": recommendations,
        "confidence": confidence,
        "sources": sources,
        "mode": mode,
    }
