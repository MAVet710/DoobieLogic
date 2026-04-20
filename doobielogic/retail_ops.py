from __future__ import annotations

from doobielogic.buyer_brain import render_buyer_brain_summary, summarize_buyer_opportunities


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def analyze_retail_execution(data: dict) -> dict:
    conversion = [float(x) for x in data.get("conversion_rate", []) if x is not None]
    atv = [float(x) for x in data.get("avg_ticket_value", []) if x is not None]
    queue = [float(x) for x in data.get("queue_wait_minutes", []) if x is not None]
    return {
        "status": "ok",
        "avg_conversion_rate": round(_avg(conversion), 3) if conversion else None,
        "avg_ticket_value": round(_avg(atv), 2) if atv else None,
        "avg_queue_wait_minutes": round(_avg(queue), 2) if queue else None,
        "queue_breach_rows": sum(1 for x in queue if x > 8),
    }


def build_retail_action_plan(mapped_data: dict) -> dict:
    insights = summarize_buyer_opportunities(mapped_data or {})
    execution = analyze_retail_execution(mapped_data or {})
    actions = []
    low = insights.get("low_velocity", {})
    if low.get("low_velocity_count", 0) > 0:
        actions.append("Review slow movers for markdown or delist decisions.")
    if insights.get("brand_concentration", {}).get("high_concentration"):
        actions.append("Reduce brand concentration risk with assortment diversification.")
    if execution.get("queue_breach_rows", 0) > 0:
        actions.append("Adjust labor coverage and express-lane SOP where queue times exceed 8 minutes.")
    if not actions:
        actions.append("Retail signals stable; keep weekly assortment review.")
    return {"insights": insights, "execution": execution, "actions": actions}


def render_retail_action_plan(summary: dict) -> str:
    return render_buyer_brain_summary(summary.get("insights", {})) + "\n" + "\n".join([f"- {a}" for a in summary.get("actions", [])])
