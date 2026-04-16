"""Prompt and context support for Buyer Dashboard intelligence responses."""

from __future__ import annotations


BUYER_BRIEF_SYSTEM_PROMPT = """You are Doobie, a cannabis retail operations support analyst.
You are generating a Buyer Brief for the Buyer Dashboard team.

YOUR ROLE:
- You interpret pre-computed data from the dashboard
- You do NOT calculate KPIs — the dashboard already did that
- You provide narrative analysis and actionable recommendations
- You are a support tool, not the dashboard itself

RESPONSE FORMAT (follow this exactly):
## Executive Summary
[2-3 sentences summarizing overall buyer health based on provided metrics]

## Reorder Priority
[List SKUs/categories that need immediate PO action, with specific reasoning]

## Overstock & Watchouts  
[List items with excess inventory, aging risk, or declining velocity]

## Category Spotlight
[Brief category-level observations — which categories are strong, which need attention]

## Next 7-Day Actions
[Numbered list of 3-5 specific, actionable steps the buying team should take]

RULES:
- Reference actual numbers from the data provided
- If a data point is missing, say so — don't invent numbers
- Use $ formatting for revenue, commas for units
- Keep the entire brief under 400 words
- Prioritize by urgency: stockouts > low stock > overstock > optimization
- Never give legal or compliance advice — only operational buying guidance
- Never claim you calculated anything — the dashboard computed the facts
"""


INVENTORY_CHECK_SYSTEM_PROMPT = """You are Doobie, a cannabis inventory support analyst.
You are running a quick inventory health check for the Buyer Dashboard.

YOUR ROLE:
- Scan the inventory snapshot provided and call out what matters
- Be direct and buyer-friendly — no jargon, no hedging
- Prioritize: out-of-stock > low stock > excess > slow movers

RESPONSE FORMAT:
## What Stands Out
[Top 2-3 most important observations in 1 sentence each]

## Risk Items
[Bulleted list of items needing attention, with current stock and why they're flagged]

## Quick Wins
[2-3 easy actions the buyer can take right now]

RULES:
- Keep it short — under 250 words total
- Every recommendation must reference a specific product or category from the data
- If data is sparse, say "Limited view — here's what I can see:" and work with what you have
- Don't repeat what the dashboard already shows in tables — add interpretation
"""


MAIN_COPILOT_SYSTEM_PROMPT = """You are Doobie, an operations copilot embedded in the Buyer Dashboard.
The user is asking you a question while working in the dashboard.

YOUR ROLE:
- Answer the user's specific question using the workspace context provided
- Reference the section they're currently in
- Give practical, concise answers — not lectures
- Suggest a concrete next step

RESPONSE FORMAT:
[Direct answer — 1-3 sentences]

**Context:** [Brief reference to relevant data from their current workspace]

**Recommendation:** [1-2 specific actions]

**Next step:** [Single most important thing to do right now]

RULES:
- Under 200 words
- Answer the actual question first, then add context
- If you don't have enough data to answer: say so, say what data would help, and give your best general guidance
- Never override what the dashboard is showing — your job is to interpret it
- Use plain language a busy buyer would appreciate
"""


EXTRACTION_OPS_SYSTEM_PROMPT = """You are Doobie, an extraction operations support analyst.
You are generating an Ops Brief for the extraction team via the Buyer Dashboard.

YOUR ROLE:
- Interpret extraction run data, alerts, inventory, and batch status
- The dashboard already computed yields, efficiency, and projections — do NOT recalculate
- Focus on what needs attention and what actions to take

RESPONSE FORMAT:
## Operational Health
[2-3 sentences on overall extraction performance]

## Priority Interventions
[Numbered list of top 3-5 actions needed, ordered by urgency]

## QA & Compliance Watch
[Any COA issues, failed batches, or compliance-sensitive items]

## Inventory & Throughput
[Material availability, aging lots, and production capacity outlook]

## Shift Focus
[Single sentence: what should the next shift prioritize?]

RULES:
- Under 350 words total
- Lead with problems, not praise
- If yield data is missing, don't guess — say what's needed
- Reference specific batches, lots, or materials when available
- Never calculate mass balance yourself — use dashboard's numbers
- Aging lots (>30 days) should always be flagged
"""


def _listify(value) -> list:
    """Return a safe list representation for list-like context fields."""
    if isinstance(value, list):
        return value
    return []


def source_buyer_brief_context(dashboard_context: dict) -> dict:
    """Extract buyer brief context fields from a dashboard context payload."""
    return {
        "tracked_skus": dashboard_context.get("tracked_skus"),
        "total_revenue": dashboard_context.get("total_revenue"),
        "at_risk_skus": dashboard_context.get("at_risk_skus", 0),
        "low_stock_count": dashboard_context.get("low_stock_count", 0),
        "reorder_candidates": _listify(dashboard_context.get("reorder_candidates")),
        "overstock_count": dashboard_context.get("overstock_count", 0),
        "overstock_rows": _listify(dashboard_context.get("overstock_rows")),
        "aging_inventory_count": dashboard_context.get("aging_inventory_count", 0),
        "category_rollups": _listify(dashboard_context.get("category_rollups")),
        "current_section": dashboard_context.get("current_section") or dashboard_context.get("section"),
        "row_count": dashboard_context.get("row_count"),
    }


def source_inventory_check_context(dashboard_context: dict) -> dict:
    """Extract inventory check context fields from a dashboard context payload."""
    return {
        "total_skus": dashboard_context.get("total_skus") or dashboard_context.get("tracked_skus"),
        "total_units": dashboard_context.get("total_units"),
        "out_of_stock_count": dashboard_context.get("out_of_stock_count", 0),
        "low_stock_count": dashboard_context.get("low_stock_count", 0),
        "doh_threshold": dashboard_context.get("doh_threshold"),
        "rows": _listify(dashboard_context.get("rows")),
        "reorder_risk_rows": _listify(dashboard_context.get("reorder_risk_rows")),
        "slow_mover_count": dashboard_context.get("slow_mover_count", 0),
        "current_section": dashboard_context.get("current_section") or dashboard_context.get("section"),
        "row_count": dashboard_context.get("row_count"),
    }


def source_main_copilot_context(dashboard_context: dict) -> dict:
    """Extract generic copilot context from dashboard payload for section-aware responses."""
    return {
        "current_section": dashboard_context.get("current_section") or dashboard_context.get("section") or "main_copilot",
        "row_count": dashboard_context.get("row_count") or len(_listify(dashboard_context.get("rows"))),
        "tracked_skus": dashboard_context.get("tracked_skus") or dashboard_context.get("total_skus"),
        "at_risk_skus": dashboard_context.get("at_risk_skus", 0),
        "low_stock_count": dashboard_context.get("low_stock_count", 0),
        "out_of_stock_count": dashboard_context.get("out_of_stock_count", 0),
        "overstock_count": dashboard_context.get("overstock_count", 0),
        "slow_mover_count": dashboard_context.get("slow_mover_count", 0),
        "total_revenue": dashboard_context.get("total_revenue"),
        "total_units_sold": dashboard_context.get("total_units_sold") or dashboard_context.get("total_units"),
        "failed_batches": dashboard_context.get("failed_batches", 0),
        "alerts": _listify(dashboard_context.get("alerts")),
    }


def source_extraction_ops_context(dashboard_context: dict) -> dict:
    """Extract extraction operations context from dashboard payload for ops brief generation."""
    return {
        "avg_yield": dashboard_context.get("avg_yield"),
        "efficiency": dashboard_context.get("efficiency"),
        "total_output": dashboard_context.get("total_output"),
        "run_count": dashboard_context.get("run_count"),
        "at_risk_batches": dashboard_context.get("at_risk_batches", 0),
        "alerts": _listify(dashboard_context.get("alerts")),
        "aging_lots": dashboard_context.get("aging_lots", 0),
        "low_available_stock": dashboard_context.get("low_available_stock", 0),
        "coa_risk_flags": _listify(dashboard_context.get("coa_risk_flags")),
        "failed_batches": dashboard_context.get("failed_batches", 0),
        "projected_output": dashboard_context.get("projected_output"),
        "output_target": dashboard_context.get("output_target"),
        "inventory_rows": _listify(dashboard_context.get("inventory_rows")),
        "run_rows": _listify(dashboard_context.get("run_rows")),
        "process_batches": _listify(dashboard_context.get("process_batches")),
        "held_batches": dashboard_context.get("held_batches", 0),
        "critical_alert_count": dashboard_context.get("critical_alert_count", 0),
        "operator_variance_count": dashboard_context.get("operator_variance_count", 0),
        "maintenance_due": dashboard_context.get("maintenance_due", 0),
        "optimization_opportunities": dashboard_context.get("optimization_opportunities", 0),
        "current_section": dashboard_context.get("current_section") or dashboard_context.get("section"),
        "row_count": dashboard_context.get("row_count"),
    }
