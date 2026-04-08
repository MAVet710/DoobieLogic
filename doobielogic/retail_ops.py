from __future__ import annotations

from doobielogic.buyer_brain import render_buyer_brain_summary, summarize_buyer_opportunities


def build_retail_action_plan(mapped_data: dict) -> dict:
    insights = summarize_buyer_opportunities(mapped_data or {})
    actions = []
    low = insights.get("low_velocity", {})
    if low.get("low_velocity_count", 0) > 0:
        actions.append("Review slow movers for markdown or delist decisions.")
    if insights.get("brand_concentration", {}).get("high_concentration"):
        actions.append("Reduce brand concentration risk with assortment diversification.")
    if not actions:
        actions.append("Retail signals stable; keep weekly assortment review.")
    return {"insights": insights, "actions": actions}


def render_retail_action_plan(summary: dict) -> str:
    return render_buyer_brain_summary(summary.get("insights", {})) + "\n" + "\n".join([f"- {a}" for a in summary.get("actions", [])])
