from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _avg(items: list[float]) -> float | None:
    if not items:
        return None
    return sum(items) / len(items)


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


def _build_inventory_summary(data: dict[str, Any]) -> dict[str, Any]:
    doh = _safe_float(data.get("days_on_hand") or data.get("doh"))
    velocity = _safe_float(data.get("velocity") or data.get("sales_velocity"))
    sell_through = _safe_float(data.get("sell_through_rate") or data.get("sell_through"))

    if doh is None:
        inv = data.get("inventory") if isinstance(data.get("inventory"), list) else []
        dohs = [_safe_float(row.get("days_on_hand")) for row in inv if isinstance(row, dict)]
        doh = _avg([d for d in dohs if d is not None])

    if velocity is None:
        inv = data.get("inventory") if isinstance(data.get("inventory"), list) else []
        vels = [_safe_float(row.get("velocity")) for row in inv if isinstance(row, dict)]
        velocity = _avg([v for v in vels if v is not None])

    if sell_through is None:
        inv = data.get("inventory") if isinstance(data.get("inventory"), list) else []
        rates = [_safe_float(row.get("sell_through_rate")) for row in inv if isinstance(row, dict)]
        sell_through = _avg([r for r in rates if r is not None])

    return {
        "days_on_hand": doh,
        "velocity": velocity,
        "sell_through_rate": sell_through,
    }


def _build_extraction_summary(data: dict[str, Any]) -> dict[str, Any]:
    method = str(data.get("method") or data.get("extraction_method") or "unknown")
    input_g = _safe_float(data.get("input_grams") or data.get("input_mass_g"))
    output_g = _safe_float(data.get("output_grams") or data.get("output_mass_g"))
    yield_percent = _safe_float(data.get("yield_percent") or data.get("yield_pct"))

    if yield_percent is None and input_g and output_g:
        yield_percent = (output_g / input_g) * 100

    return {
        "method": method,
        "input_grams": input_g,
        "output_grams": output_g,
        "yield_percent": yield_percent,
        "failed_batches": int(data.get("failed_batches") or 0),
    }


def _collect_relevant_rules(mode: str, modules: dict[str, Any]) -> list[str]:
    relevant: list[str] = []
    if mode in {"buyer", "executive"} and "buyer" in modules:
        rules = modules["buyer"].get("inventory_logic", {}).get("rules", [])
        relevant.extend([str(rule.get("id")) for rule in rules if isinstance(rule, dict)])
    if mode in {"extraction", "executive"} and "financial" in modules:
        rel = modules["financial"].get("yield_to_profit_relationships", [])
        relevant.extend([str(rule.get("id")) for rule in rel if isinstance(rule, dict)])
    if mode in {"compliance", "executive"} and "compliance" in modules:
        hl = modules["compliance"].get("high_level_rules", [])
        relevant.extend([str(rule.get("id")) for rule in hl if isinstance(rule, dict)])
    return relevant


def _risk_flags(mode: str, inventory: dict[str, Any], extraction: dict[str, Any]) -> list[str]:
    flags: list[str] = []

    doh = inventory.get("days_on_hand")
    sell_through = inventory.get("sell_through_rate")
    if mode in {"buyer", "executive"}:
        if isinstance(doh, (float, int)) and doh < 14:
            flags.append("Low DOH indicates restock risk.")
        if isinstance(doh, (float, int)) and doh > 75:
            flags.append("High DOH indicates dead inventory risk.")
        if isinstance(sell_through, (float, int)) and sell_through < 0.30:
            flags.append("Low sell-through indicates potential assortment or pricing mismatch.")

    run_yield = extraction.get("yield_percent")
    if mode in {"extraction", "executive"}:
        if isinstance(run_yield, (float, int)) and run_yield < 8:
            flags.append("Low extraction yield suggests process inefficiency or weak input quality.")
        if extraction.get("failed_batches", 0) > 0:
            flags.append("Failed batches detected; investigate QA release and stage controls.")

    return flags


def build_doobie_context(data: dict[str, Any] | None, mode: str) -> dict[str, Any]:
    data = data or {}
    safe_mode = mode if mode in {"buyer", "extraction", "compliance", "executive", "financial"} else "executive"

    module_selection = {
        "buyer": {"buyer", "taxonomy", "financial", "compliance"},
        "extraction": {"extraction", "taxonomy", "financial", "compliance"},
        "compliance": {"compliance", "taxonomy"},
        "financial": {"financial", "buyer", "extraction", "taxonomy"},
        "executive": set(INTEL_FILES.keys()),
    }

    modules = load_intel_modules(module_selection[safe_mode])
    inventory_summary = _build_inventory_summary(data)
    extraction_summary = _build_extraction_summary(data)
    risk_flags = _risk_flags(safe_mode, inventory_summary, extraction_summary)

    context = {
        "mode": safe_mode,
        "inventory_summary": inventory_summary,
        "extraction_summary": extraction_summary,
        "relevant_rules": _collect_relevant_rules(safe_mode, modules),
        "risk_flags": risk_flags,
        "intel_modules": modules,
    }
    return context


def build_ai_input(question: str, data: dict[str, Any] | None, mode: str, state: str | None = None) -> dict[str, Any]:
    context = build_doobie_context(data=data, mode=mode)
    return {
        "question": question,
        "state": state,
        "dashboard_data": data or {},
        "structured_context": {
            "inventory_summary": context["inventory_summary"],
            "extraction_summary": context["extraction_summary"],
            "relevant_rules": context["relevant_rules"],
            "risk_flags": context["risk_flags"],
        },
        "intel_modules": context["intel_modules"],
    }


def format_doobie_response(quick_answer: str, explanation: str, recommendation: list[str], risk_flags: list[str], inefficiencies: list[str]) -> dict[str, Any]:
    return {
        "quick_answer": quick_answer,
        "explanation": explanation,
        "recommendation": recommendation,
        "risk_flags": risk_flags,
        "inefficiencies": inefficiencies,
    }
