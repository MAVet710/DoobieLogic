from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from dataclasses import asdict, dataclass
from typing import Any

INTEL_DIR = Path(__file__).resolve().parent.parent / "intel"
INTEL_FILES = {
    "extraction": "extraction_intel.json",
    "buyer": "buyer_intel.json",
    "compliance": "compliance_intel.json",
    "taxonomy": "product_taxonomy.json",
    "financial": "financial_intel.json",
    "operations": "operations_intel.json",
}

MODE_TO_MODULES = {
    "buyer": {"buyer", "taxonomy", "financial", "compliance"},
    "inventory": {"buyer", "taxonomy", "financial"},
    "retail_ops": {"operations", "buyer", "taxonomy", "financial", "compliance"},
    "extraction": {"extraction", "operations", "taxonomy", "financial", "compliance"},
    "cultivation": {"operations", "taxonomy", "compliance", "financial"},
    "kitchen": {"operations", "taxonomy", "compliance", "financial"},
    "packaging": {"operations", "taxonomy", "compliance", "financial"},
    "compliance": {"compliance", "operations", "taxonomy"},
    "financial": {"financial", "buyer", "extraction", "operations", "taxonomy"},
    "executive": set(INTEL_FILES.keys()),
    "ops": {"operations", "compliance", "financial"},
}

ROLE_KEYWORDS = {
    "buyer": {"assortment", "vendor", "margin", "velocity", "doh", "promo", "sku", "pricing"},
    "inventory": {"stock", "doh", "reorder", "aging", "overstock", "velocity"},
    "retail_ops": {"conversion", "atv", "upt", "staff", "queue", "throughput", "discount", "stockout"},
    "extraction": {"yield", "biomass", "solvent", "throughput", "rework", "residual", "batch", "formulation"},
    "cultivation": {"canopy", "harvest", "room", "phenotype", "microbial", "cure", "trim", "cycle"},
    "kitchen": {"infusion", "dosage", "batch", "sanitation", "allergen", "cooling", "traceability"},
    "packaging": {"label", "lot", "reconciliation", "line", "qa", "tamper", "child", "rework"},
    "compliance": {"traceability", "audit", "capa", "manifest", "storage", "transfer", "variance"},
    "financial": {"margin", "cash", "working", "markdown", "carrying", "roi", "capital"},
    "executive": {"kpi", "capital", "risk", "bottleneck", "accountability", "leverage", "scaling"},
    "ops": {"execution", "bottleneck", "ownership", "cadence", "throughput"},
}

RISK_TERMS = {"risk", "fail", "failure", "variance", "aging", "stockout", "hold", "rework", "compliance"}


@dataclass(frozen=True)
class IntelligenceEvidence:
    source_module: str
    section: str
    rule_id: str
    value: str
    relevance: float
    citation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


@lru_cache(maxsize=16)
def _load_intel_modules_cached(selected_keys: tuple[str, ...]) -> dict[str, Any]:
    modules: dict[str, Any] = {}
    for key, filename in INTEL_FILES.items():
        if key not in selected_keys:
            continue
        path = INTEL_DIR / filename
        with path.open("r", encoding="utf-8") as f:
            modules[key] = json.load(f)
    return modules


def load_intel_modules(selected: set[str] | None = None) -> dict[str, Any]:
    wanted = tuple(sorted(selected or set(INTEL_FILES.keys())))
    return _load_intel_modules_cached(wanted)


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


def _derive_rule_identifier(module_key: str, path: str, node: Any) -> str:
    if isinstance(node, dict):
        for key in ("id", "rule_id", "identifier", "name", "title"):
            raw = node.get(key)
            if raw is not None and str(raw).strip():
                return str(raw).strip()
    stable = path.replace("[", ".").replace("]", "").replace("..", ".").strip(".")
    return f"{module_key}:{stable or 'root'}"


def _build_citation_label(module_key: str, section: str, rule_id: str) -> str:
    section_slug = section.replace("[", ".").replace("]", "").replace("..", ".").strip(".") or "root"
    clean_rule_id = rule_id
    if clean_rule_id.startswith(f"{module_key}:"):
        clean_rule_id = clean_rule_id[len(module_key) + 1 :]
    return f"[{module_key}:{clean_rule_id}@{section_slug}]"


def _flatten_items(module_key: str, prefix: str, node: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(node, dict):
        blob_parts: list[str] = []
        for key, value in node.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            rows.extend(_flatten_items(module_key, child_prefix, value))
            if not isinstance(value, (dict, list)):
                blob_parts.append(f"{key}:{value}")
        if blob_parts:
            section = prefix or "root"
            text = "; ".join(blob_parts)
            rule_id = _derive_rule_identifier(module_key, section, node)
            rows.append(
                {
                    "module": module_key,
                    "section": section,
                    "rule_id": rule_id,
                    "text": text,
                    "search_blob": f"{module_key} {section} {text} {rule_id}".lower(),
                    "citation": _build_citation_label(module_key, section, rule_id),
                }
            )
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            rows.extend(_flatten_items(module_key, f"{prefix}[{idx}]", value))
    else:
        section = prefix or "root"
        value = str(node)
        rule_id = _derive_rule_identifier(module_key, section, node)
        rows.append(
            {
                "module": module_key,
                "section": section,
                "rule_id": rule_id,
                "text": value,
                "search_blob": f"{module_key} {section} {value} {rule_id}".lower(),
                "citation": _build_citation_label(module_key, section, rule_id),
            }
        )
    return rows


def _extract_topic_terms(question: str | None, data: dict[str, Any], mode: str) -> set[str]:
    terms = {str(k).lower() for k in data.keys()}
    q = (question or "").lower()
    terms.update(token.strip(".,:;()[]{}") for token in q.split() if token)
    terms.update(ROLE_KEYWORDS.get(mode, set()))
    return {t for t in terms if t}


def _rank_intelligence(mode: str, modules: dict[str, Any], question: str | None, data: dict[str, Any], limit: int = 14) -> list[IntelligenceEvidence]:
    topic_terms = _extract_topic_terms(question, data, mode)
    scored: list[tuple[float, dict[str, Any]]] = []
    for module_key, payload in modules.items():
        for row in _flatten_items(module_key, "", payload):
            blob = row["search_blob"]
            score = 0.0
            if module_key in MODE_TO_MODULES.get(mode, set()):
                score += 3.0
            for term in topic_terms:
                if term and term in blob:
                    score += 1.7
            if any(term in blob for term in RISK_TERMS):
                score += 0.8
            if "trigger" in blob or "threshold" in blob or "rule" in blob or "heuristic" in blob:
                score += 0.5
            if score > 0:
                scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)

    selected: list[IntelligenceEvidence] = []
    seen: set[tuple[str, str, str]] = set()
    for score, row in scored:
        key = (row["module"], row["section"], row["rule_id"])
        if key in seen:
            continue
        seen.add(key)
        selected.append(
            IntelligenceEvidence(
                source_module=row["module"],
                section=row["section"],
                rule_id=row["rule_id"],
                value=row["text"],
                relevance=round(score, 3),
                citation=row["citation"],
            )
        )
        if len(selected) >= limit:
            break
    return selected


def _collect_relevant_rules(mode: str, modules: dict[str, Any]) -> list[str]:
    relevant: list[str] = []
    if mode in {"buyer", "inventory", "retail_ops", "executive"} and "buyer" in modules:
        rules = modules["buyer"].get("inventory_logic", {}).get("rules", [])
        relevant.extend([str(rule.get("id")) for rule in rules if isinstance(rule, dict)])
    if mode in {"extraction", "financial", "executive"} and "financial" in modules:
        rel = modules["financial"].get("yield_to_profit_relationships", [])
        relevant.extend([str(rule.get("id")) for rule in rel if isinstance(rule, dict)])
    if mode in {"compliance", "packaging", "kitchen", "retail_ops", "executive"} and "compliance" in modules:
        hl = modules["compliance"].get("high_level_rules", [])
        relevant.extend([str(rule.get("id")) for rule in hl if isinstance(rule, dict)])
    if mode in {"retail_ops", "cultivation", "kitchen", "packaging", "executive"} and "operations" in modules:
        dept_rules = modules["operations"].get(mode, {}).get("escalation_triggers", [])
        relevant.extend([str(rule.get("id")) for rule in dept_rules if isinstance(rule, dict)])
    return relevant


def _build_state_overlay(state: str | None, modules: dict[str, Any]) -> dict[str, Any]:
    compliance = modules.get("compliance") if isinstance(modules.get("compliance"), dict) else {}
    overlay_model = compliance.get("state_overlay_model", {}) if isinstance(compliance, dict) else {}
    safe_state = (state or "").strip().upper()
    if not safe_state:
        return {"state": None, "note": "No state provided; using baseline conservative compliance guidance."}
    return {
        "state": safe_state,
        "model": overlay_model,
        "note": (
            "State overlays are operational context only and not legal advice. "
            "Verify against current regulator publications before action."
        ),
    }


def _risk_flags(mode: str, inventory: dict[str, Any], extraction: dict[str, Any], data: dict[str, Any]) -> list[str]:
    flags: list[str] = []

    doh = inventory.get("days_on_hand")
    sell_through = inventory.get("sell_through_rate")
    if mode in {"buyer", "inventory", "retail_ops", "executive", "financial"}:
        if isinstance(doh, (float, int)) and doh < 14:
            flags.append("Low DOH indicates restock risk.")
        if isinstance(doh, (float, int)) and doh > 75:
            flags.append("High DOH indicates dead inventory risk.")
        if isinstance(sell_through, (float, int)) and sell_through < 0.30:
            flags.append("Low sell-through indicates potential assortment or pricing mismatch.")

    run_yield = extraction.get("yield_percent")
    if mode in {"extraction", "executive", "financial"}:
        if isinstance(run_yield, (float, int)) and run_yield < 8:
            flags.append("Low extraction yield suggests process inefficiency or weak input quality.")
        if extraction.get("failed_batches", 0) > 0:
            flags.append("Failed batches detected; investigate QA release and stage controls.")

    if mode in {"retail_ops", "executive"}:
        if _safe_float(data.get("conversion_rate")) is not None and float(data.get("conversion_rate")) < 0.18:
            flags.append("Conversion rate below operating threshold.")
        if _safe_float(data.get("discount_rate")) is not None and float(data.get("discount_rate")) > 0.18:
            flags.append("Discount rate above guardrail; margin quality risk.")

    if mode in {"cultivation", "executive"}:
        micro = sum(1 for x in data.get("microbial_risk_flag", []) if bool(x))
        moisture = sum(1 for x in data.get("moisture_risk_flag", []) if bool(x))
        if micro > 0:
            flags.append("Microbial risk flags detected in cultivation runs.")
        if moisture > 0:
            flags.append("Moisture risk flags indicate cure instability risk.")

    if mode in {"kitchen", "executive"}:
        if _safe_float(data.get("dosage_variance_pct")) and float(data.get("dosage_variance_pct")) > 10:
            flags.append("Dosage variance exceeds tolerance and may require hold/rework.")
        if sum(1 for x in data.get("sanitation_gap_flag", []) if bool(x)) > 0:
            flags.append("Sanitation gap flags raise release risk.")

    if mode in {"packaging", "executive", "compliance"}:
        if sum(1 for x in data.get("label_error_flag", []) if bool(x)) > 0:
            flags.append("Label error events create compliance and recall exposure.")
        if any(abs(float(x)) > 2 for x in data.get("reconciliation_variance", []) if x is not None):
            flags.append("High reconciliation variance detected in packaging records.")

    if mode in {"compliance", "executive"}:
        if any(float(x) > 30 for x in data.get("open_days", []) if x is not None):
            flags.append("Aging CAPAs increase audit and operating risk.")

    return flags


def build_doobie_context(data: dict[str, Any] | None, mode: str, question: str | None = None, state: str | None = None) -> dict[str, Any]:
    data = data or {}
    safe_mode = mode if mode in MODE_TO_MODULES else "executive"

    modules = load_intel_modules(MODE_TO_MODULES[safe_mode])
    inventory_summary = _build_inventory_summary(data)
    extraction_summary = _build_extraction_summary(data)
    risk_flags = _risk_flags(safe_mode, inventory_summary, extraction_summary, data=data)

    context = {
        "mode": safe_mode,
        "inventory_summary": inventory_summary,
        "extraction_summary": extraction_summary,
        "relevant_rules": _collect_relevant_rules(safe_mode, modules),
        "risk_flags": risk_flags,
        "selected_intelligence": [e.to_dict() for e in _rank_intelligence(safe_mode, modules, question=question, data=data)],
        "state_overlay": _build_state_overlay(state, modules),
        "intel_modules": modules,
    }
    return context


def build_ai_input(question: str, data: dict[str, Any] | None, mode: str, state: str | None = None) -> dict[str, Any]:
    context = build_doobie_context(data=data, mode=mode, question=question, state=state)
    return {
        "question": question,
        "state": state,
        "dashboard_data": data or {},
        "structured_context": {
            "inventory_summary": context["inventory_summary"],
            "extraction_summary": context["extraction_summary"],
            "relevant_rules": context["relevant_rules"],
            "risk_flags": context["risk_flags"],
            "selected_intelligence": context["selected_intelligence"],
            "state_overlay": context["state_overlay"],
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
