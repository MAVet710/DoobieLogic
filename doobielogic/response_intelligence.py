"""Pure response generation logic for Buyer Dashboard support workflows."""

from __future__ import annotations

from doobielogic.extraction_dashboard_support import (
    interpret_extraction_alerts,
    interpret_extraction_inventory,
    interpret_process_tracker,
    interpret_projected_output,
    interpret_run_log,
    prioritize_extraction_actions,
)
from doobielogic.response_templates import (
    SECTION_FRAMES,
    build_action_list,
    format_currency,
    format_number,
    format_percent,
    truncate_list,
)


def _to_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default: int = 0) -> int:
    """Safely convert a value to int."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _buyer_exec_summary(context: dict) -> str:
    """Build the executive summary section for buyer brief responses."""
    revenue = context.get("total_revenue")
    tracked = context.get("tracked_skus")
    at_risk = _to_int(context.get("at_risk_skus"), 0)
    if revenue is not None and tracked is not None:
        base = f"Across {format_number(tracked)} tracked SKUs generating {format_currency(revenue)} in revenue"
    else:
        return "Revenue data not available in current context. Focus shifts to inventory movement signals."

    if _to_int(tracked, 0) <= 0 or at_risk <= 0:
        return base + ", no immediate risk concentration flags were detected."

    ratio = at_risk / _to_int(tracked, 1)
    if ratio > 0.15:
        tone = "Significant risk concentration"
    elif ratio <= 0.05:
        tone = "Risk profile is manageable"
    else:
        tone = "Risk is present and should be managed proactively"
    return f"{base}, with {format_number(at_risk)} at-risk SKUs ({format_percent(ratio * 100)}). {tone}."


def _buyer_reorder_section(context: dict) -> str:
    """Build reorder priority markdown text using low-stock and reorder candidate context."""
    lines: list[str] = []
    low_stock = _to_int(context.get("low_stock_count"), 0)
    if low_stock > 0:
        lines.append(f"**{format_number(low_stock)} SKUs are at or below reorder threshold** — these need PO action this week.")

    candidates = truncate_list(context.get("reorder_candidates", []) or [], max_items=10)
    for row in candidates:
        lines.append(
            "- "
            f"{row.get('product_name', 'Unknown product')}: "
            f"{format_number(row.get('current_stock'))} units remaining, "
            f"{format_number(row.get('days_on_hand'))} DOH, "
            f"avg velocity {format_number(row.get('velocity'))}/week"
        )

    if not lines:
        lines.append("Reorder candidates not identified in current data. Verify DOH thresholds are configured in the dashboard.")
    return "\n".join(lines)


def _buyer_overstock_section(context: dict) -> str:
    """Build overstock and watchout text from overstock and aging inventory signals."""
    lines: list[str] = []
    overstock = _to_int(context.get("overstock_count"), 0)
    tracked = _to_int(context.get("tracked_skus"), 0)
    tracked_safe = max(tracked, 1)
    if overstock > 0:
        lines.append(f"**{format_number(overstock)} SKUs show excess inventory pressure.**")

    for row in truncate_list(context.get("overstock_rows", []) or [], max_items=8):
        lines.append(
            "- "
            f"{row.get('product_name', 'Unknown product')}: "
            f"{format_number(row.get('inventory'))} units, "
            f"{format_number(row.get('days_on_hand'))} DOH — consider markdown or bundle strategy"
        )

    if tracked > 0 and overstock / tracked_safe > 0.2:
        lines.append("Heavy overstock concentration. Recommend immediate markdown review meeting.")
    if _to_int(context.get("aging_inventory_count"), 0) > 0:
        lines.append(f"Aging inventory watchout: {format_number(context.get('aging_inventory_count'))} SKUs beyond preferred age window.")
    if not lines:
        lines.append("Overstock analysis requires inventory and velocity fields. Not enough data to assess.")
    return "\n".join(lines)


def _buyer_category_section(context: dict) -> str:
    """Build category risk section using category rollups and risk levels."""
    rollups = context.get("category_rollups", []) or []
    if not rollups:
        return "Category risk rollups were not provided in current context."

    lines: list[str] = []
    highs: list[dict] = []
    mediums: list[dict] = []
    for row in rollups:
        level = str(row.get("risk_level") or "").lower()
        if level == "high":
            highs.append(row)
        elif level == "medium":
            mediums.append(row)

    for row in highs:
        lines.append(f"⚠️ {row.get('category', 'Unknown')}: {format_currency(row.get('revenue'))} revenue but elevated risk — review SKU-level detail")
    if mediums:
        lines.append("Medium risk categories: " + ", ".join(str(row.get("category", "Unknown")) for row in mediums[:5]))

    top_cat = max(rollups, key=lambda item: _to_float(item.get("revenue"), 0)).get("category", "N/A")
    risk_cat = highs[0].get("category", "N/A") if highs else (mediums[0].get("category", "N/A") if mediums else "N/A")
    lines.append(f"Top performing category: {top_cat}. Most at-risk: {risk_cat}.")
    return "\n".join(lines)


def _buyer_actions_section(context: dict) -> str:
    """Generate prioritized 7-day buyer actions from context signals."""
    actions: list[str] = []
    low_stock = _to_int(context.get("low_stock_count"), 0)
    overstock = _to_int(context.get("overstock_count"), 0)
    tracked = _to_int(context.get("tracked_skus"), 0)
    at_risk = _to_int(context.get("at_risk_skus"), 0)
    tracked_safe = max(tracked, 1)

    if context.get("reorder_candidates"):
        actions.append(f"Process POs for {format_number(low_stock)} low-stock SKUs")
    if overstock > 0:
        actions.append(f"Review markdown candidates — {format_number(overstock)} SKUs above DOH target")
    if tracked > 0 and at_risk / tracked_safe > 0.10:
        actions.append(f"Schedule risk review for {format_number(at_risk)} flagged SKUs")
    actions.append("Validate current DOH thresholds against last 30-day velocity")

    high_risk = [row for row in context.get("category_rollups", []) if str(row.get("risk_level") or "").lower() == "high"]
    if high_risk:
        actions.append(f"Deep-dive {high_risk[0].get('category', 'priority')} category for SKU-level intervention")
    if len(actions) == 1 and not context.get("reorder_candidates") and overstock == 0:
        return "Data is limited. Recommended: upload fresh inventory + sales data and re-run brief."
    return build_action_list(actions, max_actions=5)


def generate_buyer_brief_response(context: dict) -> str:
    """Generate a full markdown buyer brief narrative from sourced buyer context."""
    return "\n\n".join(
        [
            "## Executive Summary\n" + _buyer_exec_summary(context),
            "## Reorder Now\n" + _buyer_reorder_section(context),
            "## Overstock / Watchouts\n" + _buyer_overstock_section(context),
            "## Category Risk\n" + _buyer_category_section(context),
            "## Next 7-Day Actions\n" + _buyer_actions_section(context),
        ]
    )


def generate_inventory_check_response(context: dict) -> str:
    """Generate a markdown inventory health check from inventory-focused dashboard context."""
    rows = context.get("rows", []) or []
    total_skus = _to_int(context.get("total_skus"), len(rows))
    total_units = _to_float(context.get("total_units"), sum(_to_float(row.get("inventory"), 0) for row in rows))
    out_of_stock = _to_int(context.get("out_of_stock_count"), 0)
    low_stock = _to_int(context.get("low_stock_count"), 0)

    stands_out = [f"View includes {format_number(total_skus)} SKUs and {format_number(total_units)} total units."]
    if out_of_stock > 0:
        stands_out.append(f"🔴 **{format_number(out_of_stock)} SKUs are out of stock** — lost sales risk is active")
    if low_stock > 0:
        stands_out.append(f"🟡 **{format_number(low_stock)} SKUs below safety stock**")
    if out_of_stock == 0 and low_stock == 0:
        stands_out.append("Stock levels appear healthy across the filtered view.")

    threshold = context.get("doh_threshold")
    rows_over = []
    if threshold is not None:
        rows_over = [row for row in rows if _to_float(row.get("days_on_hand"), 0) > _to_float(threshold, float("inf"))]
    if threshold is not None and rows_over:
        stands_out.append(f"**{format_number(len(rows_over))} SKUs exceed your {format_number(threshold)}-day target** — these are tying up capital")

    risk_items: list[str] = []
    for row in (context.get("reorder_risk_rows", []) or [])[:5]:
        risk_items.append(
            "- "
            f"{row.get('product_name', 'Unknown product')}: "
            f"{format_number(row.get('current_stock'))} in stock, velocity {format_number(row.get('velocity'))}/week, "
            f"projected stockout {row.get('projected_stockout_date') or 'N/A'}"
        )

    dead_stock = [row for row in rows if _to_float(row.get("inventory"), 0) > 0 and _to_float(row.get("sales"), 0) <= 0]
    if dead_stock:
        risk_items.append(f"Dead stock candidates: {format_number(len(dead_stock))} SKUs with inventory but no recent movement")
    if _to_int(context.get("slow_mover_count"), 0) > 0:
        risk_items.append(f"Slow movers flagged: {format_number(context.get('slow_mover_count'))} SKUs")
    if not risk_items:
        risk_items.append("No immediate SKU-level risk rows were provided in this snapshot.")

    recs: list[str] = []
    for row in (context.get("reorder_risk_rows", []) or [])[:4]:
        recs.append(f"Reorder {row.get('product_name', 'priority SKU')} — you have {format_number(row.get('days_on_hand'))} days of stock left at current velocity")
    for row in rows_over[:2]:
        recs.append(f"Consider markdown on {row.get('product_name', 'overstocked SKU')} — {format_number(row.get('days_on_hand'))} days on hand with declining velocity")
    if len(rows_over) >= 2:
        recs.append(
            "Bundle opportunity: "
            f"{rows_over[0].get('product_name', 'SKU A')} and {rows_over[1].get('product_name', 'SKU B')} are both overstocked "
            f"in {rows_over[0].get('category', 'the same category')}"
        )
    if not recs:
        recs.append("Inventory view is limited. To get better recommendations: ensure the dashboard has current stock levels, sales velocity, and DOH calculations loaded.")

    return "\n\n".join(
        [
            "## What Stands Out\n" + "\n".join(stands_out[:4]),
            "## Obvious Risks\n" + "\n".join(risk_items[:8]),
            "## Recommendations\n" + "\n".join(f"- {item}" for item in recs[:8]),
        ]
    )


def _detect_intent(question: str) -> str:
    """Infer user intent from common dashboard copilot keyword groups."""
    text = (question or "").lower()
    mapping = {
        "velocity": ["slow movers", "not moving", "dead stock"],
        "reorder": ["reorder", "po", "purchase order", "buy"],
        "profitability": ["margin", "profit", "cost"],
        "risk": ["risk", "at risk", "danger"],
        "assortment": ["category", "brand", "mix"],
        "extraction": ["extraction", "yield", "batch"],
        "compliance": ["compliance", "metrc", "tracking"],
    }
    for intent, keywords in mapping.items():
        if any(token in text for token in keywords):
            return intent
    return "general"


def generate_copilot_response(context: dict, question: str) -> str:
    """Generate a concise section-aware copilot response for an in-dashboard question."""
    intent = _detect_intent(question)
    section = context.get("current_section") or "main_copilot"
    frame = SECTION_FRAMES.get(section, SECTION_FRAMES["main_copilot"])
    row_count = _to_int(context.get("row_count"), 0)

    if intent == "velocity":
        direct = f"In your {section} workspace, movement risk is the key issue: prioritize SKUs with low velocity and high days on hand."
    elif intent == "reorder":
        direct = f"In your {section} workspace, reorder timing should be the focus — prevent stockouts before the next PO cycle closes."
    elif intent == "extraction" or section == "extraction_overview":
        direct = f"In your {section} workspace, extraction stability is the priority: keep yield and QA signals tightly managed."
    elif intent == "general":
        direct = f"Based on your current {section} workspace with {format_number(row_count)} rows loaded: here's what stands out."
    else:
        direct = f"In your {section} workspace, {intent} signals deserve immediate attention before optimization work."

    support = [
        f"{frame.get('intro', 'Looking at this workspace')}, the focus is {frame.get('focus', 'current operational signals')}",
        f"Context metrics: tracked SKUs {format_number(context.get('tracked_skus'))}, at-risk SKUs {format_number(context.get('at_risk_skus'))}, low stock {format_number(context.get('low_stock_count'))}",
        f"Additional context: out-of-stock {format_number(context.get('out_of_stock_count'))}, overstock {format_number(context.get('overstock_count'))}, slow movers {format_number(context.get('slow_mover_count'))}",
    ]

    typical_actions = frame.get("typical_actions", [])
    first_action = typical_actions[0] if len(typical_actions) > 0 else "review priority risks"
    second_action = typical_actions[1] if len(typical_actions) > 1 else "align immediate mitigation owners"
    actions = [
        "What I'd recommend:",
        f"- Start with {first_action}",
        f"- Then {second_action}",
        "- Confirm thresholds and ownership before the next refresh cycle",
    ]
    next_step = "Next step: " + actions[1].replace("- ", "")
    return "\n".join([direct] + support + actions + [next_step])


def generate_extraction_ops_response(context: dict) -> str:
    """Generate an extraction operations brief using run, alert, inventory, and QA context."""
    avg_yield = context.get("avg_yield")
    efficiency = context.get("efficiency")
    output = context.get("total_output")
    run_count = context.get("run_count")

    health: list[str] = []
    if avg_yield is None:
        health.append("Yield/efficiency data not available. Dashboard should provide avg_yield, efficiency, and run counts.")
    else:
        yield_val = _to_float(avg_yield)
        if yield_val < 60:
            health.append(f"⚠️ Average yield at {yield_val:.1f}% — below target, investigate input material quality")
        elif yield_val <= 75:
            health.append("Yield is in acceptable range but has room for optimization")
        else:
            health.append(f"Yield performance is strong at {yield_val:.1f}%")
    if efficiency is not None:
        eff_val = _to_float(efficiency)
        health.append(f"Efficiency is {eff_val:.1f}%" + (" — equipment utilization needs attention" if eff_val < 70 else ""))
    if output is not None:
        health.append(f"Total output: {format_number(output)} units across {format_number(run_count)} runs")

    interventions: list[str] = []
    if _to_int(context.get("at_risk_batches"), 0) > 0:
        interventions.append(f"**{format_number(context.get('at_risk_batches'))} batches flagged at-risk** — prioritize QA review")
    alerts = context.get("alerts", []) or []
    if alerts:
        interventions.append(interpret_extraction_alerts(alerts))
    if _to_int(context.get("aging_lots"), 0) > 0:
        interventions.append(f"**{format_number(context.get('aging_lots'))} lots aging beyond target** — these consume capacity and degrade quality")
    if _to_int(context.get("low_available_stock"), 0) > 0:
        interventions.append(f"**{format_number(context.get('low_available_stock'))} materials running low** — schedule procurement before production gaps")
    if not interventions:
        interventions.append("No acute extraction interventions were detected from current context.")

    qa = []
    if context.get("coa_risk_flags"):
        qa.extend(f"- COA flag: {row.get('batch_id', 'unknown batch')} — {row.get('issue', 'risk detected')}" for row in context.get("coa_risk_flags", [])[:5])
    if _to_int(context.get("failed_batches"), 0) > 0:
        qa.append(f"⚠️ {format_number(context.get('failed_batches'))} failed batches require immediate CAPA")
    if not qa:
        qa.append("COA/QA data not loaded. Recommend checking compliance panel.")

    throughput = [interpret_projected_output(context)]
    if context.get("inventory_rows"):
        throughput.append(interpret_extraction_inventory(context.get("inventory_rows", [])))
    if context.get("run_rows"):
        throughput.append(interpret_run_log(context.get("run_rows", [])))
    if context.get("process_batches"):
        throughput.append(interpret_process_tracker(context.get("process_batches", [])))

    actions = prioritize_extraction_actions(context)
    shift_focus = f"Focus next shift on: {actions[0] if actions else 'standard operational monitoring and QA alignment'}"
    return "\n\n".join(
        [
            "## Operational Health\n" + "\n".join(health),
            "## Top Interventions\n" + "\n".join(f"- {line}" for line in interventions[:5]),
            "## QA / COA Watchouts\n" + "\n".join(qa[:6]),
            "## Throughput & Inventory Recommendations\n" + "\n".join(f"- {line}" for line in throughput[:5]),
            "## Shift Focus\n" + shift_focus,
        ]
    )
