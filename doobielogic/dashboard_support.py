from __future__ import annotations

import json
from typing import Any


def _listify(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _trim_rows(value: Any, limit: int) -> list[dict]:
    rows = _listify(value)
    out: list[dict] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
        if len(out) >= limit:
            break
    return out


def _first_present(source: dict, keys: list[str], default: Any = None) -> Any:
    for key in keys:
        if key in source and source.get(key) is not None:
            return source.get(key)
    return default


def _context_meta(context: dict, required_keys: list[str]) -> dict:
    available = sorted([key for key in required_keys if context.get(key) not in (None, [], {}, "")])
    missing = sorted([key for key in required_keys if key not in available])
    return {"available_fields": available, "missing_fields": missing}


def source_buyer_brief_context(dashboard_context: dict) -> dict:
    context = dashboard_context or {}
    category_rows = _trim_rows(_first_present(context, ["category_rows", "top_category_rows", "category_rollups", "category_summary"], []), limit=8)
    risk_sku_rows = _trim_rows(_first_present(context, ["risk_sku_rows", "top_risk_skus", "at_risk_rows"], []), limit=20)
    low_stock_rows = _trim_rows(_first_present(context, ["low_stock_rows", "low_stock_skus"], []), limit=20)
    overstock_rows = _trim_rows(_first_present(context, ["overstock_rows", "aging_rows", "slow_mover_rows"], []), limit=20)

    sourced = {
        "tracked_skus": context.get("tracked_skus", 0),
        "total_units_sold": context.get("total_units_sold", 0),
        "total_revenue": context.get("total_revenue", 0),
        "at_risk_skus": context.get("at_risk_skus", len(risk_sku_rows)),
        "category_rows": category_rows,
        "risk_sku_rows": risk_sku_rows,
        "low_stock_count": context.get("low_stock_count", len(low_stock_rows)),
        "overstock_count": context.get("overstock_count", len(overstock_rows)),
        "store_context": {
            "store_name": context.get("store_name", context.get("location_name", "Unknown store")),
            "market": context.get("market", context.get("state", "Unknown market")),
            "period": context.get("period", context.get("date_range", "Current period")),
        },
    }
    sourced["context_used"] = _context_meta(
        sourced,
        ["tracked_skus", "total_units_sold", "total_revenue", "at_risk_skus", "category_rows", "risk_sku_rows", "low_stock_count", "overstock_count", "store_context"],
    )
    return sourced


def source_inventory_check_context(dashboard_context: dict) -> dict:
    context = dashboard_context or {}
    filtered_inventory = _trim_rows(_first_present(context, ["filtered_inventory", "inventory_view", "inventory_rows"], []), limit=30)
    reorder_rows = _trim_rows(_first_present(context, ["reorder_rows", "reorder_risk_rows"], []), limit=20)
    oos_rows = _trim_rows(_first_present(context, ["oos_rows", "out_of_stock_rows"], []), limit=20)
    low_stock_rows = _trim_rows(_first_present(context, ["low_stock_rows", "low_stock_skus"], []), limit=20)
    category_summary = _trim_rows(_first_present(context, ["category_summary", "category_rows", "category_rollups"], []), limit=8)

    sourced = {
        "filtered_inventory": filtered_inventory,
        "doh_threshold": context.get("doh_threshold", context.get("days_on_hand_threshold")),
        "reorder_rows": reorder_rows,
        "oos_rows": oos_rows,
        "low_stock_rows": low_stock_rows,
        "category_summary": category_summary,
    }
    sourced["context_used"] = _context_meta(
        sourced,
        ["filtered_inventory", "doh_threshold", "reorder_rows", "oos_rows", "low_stock_rows", "category_summary"],
    )
    return sourced


def source_main_copilot_context(dashboard_context: dict) -> dict:
    context = dashboard_context or {}
    inventory_rows = _listify(_first_present(context, ["filtered_inventory", "inventory_rows"], []))
    sales_rows = _listify(_first_present(context, ["sales_rows", "trend_rows"], []))
    extraction_rows = _listify(_first_present(context, ["extraction_rows", "run_rows"], []))
    sourced = {
        "workspace": _first_present(context, ["workspace", "current_workspace", "mode"], "general"),
        "section_name": _first_present(context, ["section_name", "current_section"], "overview"),
        "row_counts": {
            "inventory_rows": context.get("inventory_row_count", len(inventory_rows)),
            "sales_rows": context.get("sales_row_count", len(sales_rows)),
            "extraction_rows": context.get("extraction_row_count", len(extraction_rows)),
        },
        "key_metrics": context.get("key_metrics", context.get("metrics", {})),
        "state_snapshot": context.get("state_snapshot", context.get("filters", {})),
    }
    sourced["context_used"] = _context_meta(
        sourced,
        ["workspace", "section_name", "row_counts", "key_metrics", "state_snapshot"],
    )
    return sourced


def source_extraction_ops_context(dashboard_context: dict) -> dict:
    context = dashboard_context or {}
    alerts = _trim_rows(_first_present(context, ["extraction_alerts", "alerts"], []), limit=20)
    run_summary_rows = _trim_rows(_first_present(context, ["run_summary_rows", "ecc_run_log", "extraction_runs"], []), limit=20)
    aging_lots = _trim_rows(_first_present(context, ["aging_lots", "lot_aging_rows"], []), limit=20)
    low_stock_lots = _trim_rows(_first_present(context, ["low_stock_lots", "low_material_rows"], []), limit=20)
    sourced = {
        "extraction_alerts": alerts,
        "run_summary_rows": run_summary_rows,
        "at_risk_batch_count": context.get("at_risk_batch_count", context.get("at_risk_batches", len(alerts))),
        "process_tracker_context": context.get("process_tracker_context", context.get("process_tracker", {})),
        "extraction_inventory_context": context.get("extraction_inventory_context", context.get("extraction_inventory", {})),
        "projected_output_totals": context.get("projected_output_totals", context.get("projected_output", {})),
        "aging_lots": aging_lots,
        "low_stock_lot_count": context.get("low_stock_lot_count", len(low_stock_lots)),
        "low_stock_lots": low_stock_lots,
    }
    sourced["context_used"] = _context_meta(
        sourced,
        [
            "extraction_alerts",
            "run_summary_rows",
            "at_risk_batch_count",
            "process_tracker_context",
            "extraction_inventory_context",
            "projected_output_totals",
            "aging_lots",
            "low_stock_lot_count",
        ],
    )
    return sourced


def _json_block(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False, indent=2)


def build_buyer_brief_prompt(context: dict) -> tuple[str, str]:
    system_prompt = (
        "You are Doobie, a support analyst for Buyer Dashboard. "
        "Do not replace dashboard calculations, KPIs, filters, routing, or UI logic. "
        "Use only provided context. Keep it concise and practical."
    )
    user_prompt = (
        "Mode: buyer_brief\n"
        "Format: executive summary -> reorder now -> overstock/watchouts -> next 7-day actions.\n"
        "If data is missing, say so plainly and provide best-next-step guidance.\n"
        f"Context:\n{_json_block(context)}"
    )
    return system_prompt, user_prompt


def build_inventory_check_prompt(context: dict) -> tuple[str, str]:
    system_prompt = (
        "You are Doobie, supporting Buyer Dashboard inventory interpretation. "
        "Never invent KPI values or compliance requirements."
    )
    user_prompt = (
        "Mode: inventory_check\n"
        "Format: what stands out -> obvious risks -> buyer-friendly recommendations.\n"
        "Short and punchy.\n"
        f"Context:\n{_json_block(context)}"
    )
    return system_prompt, user_prompt


def build_main_copilot_prompt(context: dict, user_question: str) -> tuple[str, str]:
    system_prompt = (
        "You are Doobie main copilot for Buyer Dashboard support. "
        "Answer directly, stay grounded in provided context, and do not take over app logic."
    )
    user_prompt = (
        "Mode: main_copilot\n"
        f"Question: {user_question or 'No question provided.'}\n"
        "Answer directly, reference current section, then suggest practical next steps.\n"
        f"Context:\n{_json_block(context)}"
    )
    return system_prompt, user_prompt


def build_extraction_ops_prompt(context: dict) -> tuple[str, str]:
    system_prompt = (
        "You are Doobie extraction operations support for Buyer Dashboard. "
        "Interpret extraction alerts and run context only; do not recalculate mass balance."
    )
    user_prompt = (
        "Mode: extraction_ops_brief\n"
        "Format: operational health summary -> top interventions -> QA/COA watchouts -> throughput/inventory recommendations.\n"
        "Focus on what to do next, yield risk areas, lot prioritization, and inventory pressure.\n"
        f"Context:\n{_json_block(context)}"
    )
    return system_prompt, user_prompt
