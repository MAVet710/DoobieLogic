"""Shared response templates, tone rules, and formatting helpers for dashboard support."""

from __future__ import annotations


DOOBIE_IDENTITY = """You are a support analyst assisting the Buyer Dashboard team.
You interpret pre-computed data — you do NOT calculate KPIs yourself.
You provide concise, practical, action-oriented narrative analysis.
You never claim to own the dashboard or its metrics.
You always ground your statements in the data provided.
If data is missing, you say so plainly and suggest what's needed."""


TONE_RULES = {
    "urgent": "Use direct, action-oriented language. Lead with the problem. No hedging.",
    "stable": "Use confident, measured language. Acknowledge health, then note watchpoints.",
    "limited_data": "Be transparent about gaps. Suggest what data to load. Still provide any useful guidance you can.",
    "mixed": "Lead with the most critical signal, then balance with stable areas.",
}


SECTION_FRAMES = {
    "inventory_dashboard": {
        "intro": "Looking at your inventory dashboard",
        "focus": "stock levels, DOH, reorder signals, and velocity",
        "typical_actions": ["reorder low-stock items", "markdown slow movers", "review DOH outliers"],
    },
    "trends": {
        "intro": "Based on the trends view",
        "focus": "movement direction, velocity shifts, and emerging patterns",
        "typical_actions": ["investigate declining SKUs", "capitalize on trending items", "adjust forecasts"],
    },
    "slow_movers": {
        "intro": "Reviewing your slow mover analysis",
        "focus": "items with low velocity, high DOH, and markdown potential",
        "typical_actions": ["markdown or bundle", "discontinue dead stock", "redirect shelf space"],
    },
    "po_builder": {
        "intro": "Supporting your purchase order planning",
        "focus": "reorder quantities, vendor lead times, and stock coverage",
        "typical_actions": ["confirm reorder quantities", "validate vendor selections", "check lead time assumptions"],
    },
    "buyer_intelligence": {
        "intro": "From your buyer intelligence panel",
        "focus": "category performance, brand mix, and strategic opportunities",
        "typical_actions": ["rebalance category mix", "evaluate new vendors", "review brand concentration"],
    },
    "extraction_overview": {
        "intro": "Looking at extraction operations",
        "focus": "yield, throughput, batch quality, and equipment utilization",
        "typical_actions": ["investigate low-yield batches", "schedule maintenance", "review QA flags"],
    },
    "run_analytics": {
        "intro": "Based on run-level analytics",
        "focus": "individual run performance, operator variance, and output consistency",
        "typical_actions": ["coach underperforming operators", "standardize SOPs", "investigate outlier runs"],
    },
    "process_tracker": {
        "intro": "From the process tracker",
        "focus": "batch progression, status aging, and bottleneck identification",
        "typical_actions": ["clear aging holds", "escalate stuck batches", "rebalance queue"],
    },
    "extraction_inventory": {
        "intro": "Reviewing extraction inventory",
        "focus": "material availability, lot aging, and stock coverage for production",
        "typical_actions": ["procure low materials", "prioritize aging lots", "verify lot COAs"],
    },
    "toll_processing": {
        "intro": "Looking at toll processing status",
        "focus": "partner batch status, quality agreements, and turnaround performance",
        "typical_actions": ["follow up on delayed batches", "review partner scorecards", "verify COA compliance"],
    },
    "compliance_metrc": {
        "intro": "Checking METRC/compliance alignment",
        "focus": "package tracking, manifest accuracy, and reconciliation status",
        "typical_actions": ["reconcile discrepancies", "close open manifests", "audit package IDs"],
    },
    "extraction_data_input": {
        "intro": "Supporting extraction data entry",
        "focus": "data completeness, input validation, and batch record accuracy",
        "typical_actions": ["complete missing fields", "validate entries", "flag data quality issues"],
    },
    "main_copilot": {
        "intro": "As your operations support copilot",
        "focus": "whatever you're working on right now",
        "typical_actions": ["answer your question", "highlight what stands out", "suggest next steps"],
    },
}


FALLBACK_RESPONSES = {
    "buyer_brief": (
        "**Buyer Brief — Limited Data**\n\n"
        "Not enough context was provided to generate a full buyer brief. "
        "To get actionable insights, the dashboard should send:\n"
        "- Total tracked SKUs and revenue\n"
        "- At-risk SKU count and details\n"
        "- Category rollups with risk levels\n"
        "- Low-stock and overstock counts\n\n"
        "**In the meantime:** Review your DOH report for any SKUs exceeding your target threshold, "
        "and check for items with zero movement in the last 14 days."
    ),
    "inventory_check": (
        "**Inventory Check — Limited Data**\n\n"
        "Inventory context is limited, but here's general guidance:\n"
        "- Low-stock review should be your first focus\n"
        "- Check for items below safety stock thresholds\n"
        "- Review any items with 0 units and active demand\n\n"
        "Load a filtered inventory view with DOH and velocity columns for a full check."
    ),
    "main_copilot": (
        "I don't have enough context loaded to give a specific answer. "
        "Make sure the dashboard is sending the current section, row counts, and relevant metrics. "
        "In the meantime, what specific area would you like me to focus on?"
    ),
    "extraction_ops": (
        "**Extraction Ops Brief — Limited Data**\n\n"
        "Extraction data is not fully loaded. To generate an ops brief, the dashboard should provide:\n"
        "- Recent run summaries (yield, output, efficiency)\n"
        "- Active alerts and at-risk batches\n"
        "- Extraction inventory levels and aging lots\n\n"
        "**General guidance:** Focus on clearing any batches stuck in QA hold, "
        "and verify input material availability before scheduling next runs."
    ),
}


def determine_risk_tone(context: dict) -> str:
    """Analyze context signals to determine overall response tone."""
    urgent_signals = 0
    try:
        tracked_skus = float(context.get("tracked_skus", 1) or 1)
    except (TypeError, ValueError):
        tracked_skus = 1.0
    if context.get("out_of_stock_count", 0) > 0:
        urgent_signals += 1
    if context.get("at_risk_skus", 0) > tracked_skus * 0.15:
        urgent_signals += 1
    if context.get("failed_batches", 0) > 0:
        urgent_signals += 1
    if context.get("aging_lots", 0) > 5:
        urgent_signals += 1

    key_fields = ["tracked_skus", "total_revenue", "total_units_sold"]
    available = sum(1 for field in key_fields if context.get(field) is not None)

    if available < 2:
        return "limited_data"
    if urgent_signals >= 2:
        return "urgent"
    if urgent_signals == 1:
        return "mixed"
    return "stable"


def format_currency(value) -> str:
    """Format a value as currency, returning N/A on invalid input."""
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "N/A"


def format_number(value) -> str:
    """Format a value as a comma-separated whole number, returning N/A on invalid input."""
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return "N/A"


def format_percent(value) -> str:
    """Format a value as a percentage, returning N/A on invalid input."""
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def safe_get(d: dict, *keys, default=None):
    """Safely access nested dictionary keys, returning default when missing."""
    current = d
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def truncate_list(items: list, max_items: int = 10, label: str = "items") -> list:
    """Return a list truncated to max_items while keeping ordering."""
    _ = label
    if len(items) <= max_items:
        return items
    return items[:max_items]


def build_action_list(actions: list[str], max_actions: int = 5) -> str:
    """Format actions as a numbered markdown list."""
    trimmed = actions[:max_actions]
    return "\n".join(f"{index + 1}. {action}" for index, action in enumerate(trimmed))
