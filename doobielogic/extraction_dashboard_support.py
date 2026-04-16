"""Extraction-focused interpretation helpers for dashboard support responses."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone


def _to_float(value, default: float = 0.0) -> float:
    """Safely parse a numeric value into float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _hours_since(value) -> float:
    """Return hours elapsed from an ISO timestamp, or 0 when invalid."""
    if not value:
        return 0.0
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    now = datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return max((now - stamp).total_seconds() / 3600, 0.0)


def interpret_run_log(runs: list[dict]) -> str:
    """Interpret extraction run logs and summarize yield, method, and operator variance."""
    if not runs:
        return "No extraction run log data available in current context."

    yields = [_to_float(run.get("yield_pct"), default=-1) for run in runs]
    valid_yields = [value for value in yields if value >= 0]
    avg_yield = sum(valid_yields) / len(valid_yields) if valid_yields else 0.0

    method_yields: dict[str, list[float]] = defaultdict(list)
    operator_yields: dict[str, list[float]] = defaultdict(list)
    low_yield = 0
    flagged_status = 0
    for run in runs:
        run_yield = _to_float(run.get("yield_pct"), default=-1)
        method = str(run.get("method") or "unknown")
        operator = str(run.get("operator") or "unknown")
        status = str(run.get("status") or "").lower()
        if run_yield >= 0:
            method_yields[method].append(run_yield)
            operator_yields[operator].append(run_yield)
        if 0 <= run_yield < 50:
            low_yield += 1
        if status in {"hold", "failed"}:
            flagged_status += 1

    method_avg = {k: sum(v) / len(v) for k, v in method_yields.items() if v}
    best_method = max(method_avg, key=method_avg.get) if method_avg else "N/A"
    best_method_yield = method_avg.get(best_method, 0.0)
    high_variance_ops = 0
    for op_yields in operator_yields.values():
        if op_yields and abs((sum(op_yields) / len(op_yields)) - avg_yield) > 10:
            high_variance_ops += 1

    return (
        f"Across {len(runs)} runs: avg yield {avg_yield:.1f}%, {best_method} performing best at {best_method_yield:.1f}%. "
        f"Low-yield runs (<50%): {low_yield}. Operator variance alerts: {high_variance_ops}. "
        f"Runs in hold/failed status: {flagged_status}."
    )


def interpret_extraction_alerts(alerts: list[dict]) -> str:
    """Interpret extraction alerts by severity and alert type for quick triage."""
    if not alerts:
        return "No active extraction alerts detected in current data."

    severity_counts = Counter(str(alert.get("severity") or "info").lower() for alert in alerts)
    type_counts = Counter(str(alert.get("alert_type") or "other").lower() for alert in alerts)

    critical = severity_counts.get("critical", 0)
    warning = severity_counts.get("warning", 0)
    info = severity_counts.get("info", 0)
    top_types = ", ".join(f"{name}: {count}" for name, count in type_counts.most_common(3))
    return (
        f"🔴 {critical} critical alerts requiring immediate attention, "
        f"{warning} warnings, {info} info alerts. Top alert types: {top_types or 'none'}."
    )


def interpret_process_tracker(batches: list[dict]) -> str:
    """Interpret batch process tracking to identify stuck work and bottlenecks."""
    if not batches:
        return "No process tracker batches available in current context."

    stuck_batches = 0
    progress_ratios: list[float] = []
    step_counts: Counter[str] = Counter()
    for batch in batches:
        if _hours_since(batch.get("status_since")) > 48:
            stuck_batches += 1
        total_steps = _to_float(batch.get("total_steps"), default=0)
        current_step = _to_float(batch.get("current_step"), default=0)
        if total_steps > 0:
            progress_ratios.append(min(current_step / total_steps, 1.0))
        step_counts[str(batch.get("current_step") or "unknown")] += 1

    avg_progress = (sum(progress_ratios) / len(progress_ratios) * 100) if progress_ratios else 0.0
    bottleneck = step_counts.most_common(1)[0][0] if step_counts else "unknown"
    return (
        f"Process tracker shows {len(batches)} active batches, {stuck_batches} stuck >48 hours. "
        f"Average progression is {avg_progress:.1f}% complete, with bottleneck concentration at step {bottleneck}."
    )


def interpret_extraction_inventory(inventory: list[dict]) -> str:
    """Interpret extraction inventory for aging lots, low-stock pressure, and COA risk."""
    if not inventory:
        return "No extraction inventory snapshot available in current context."

    total_weight = 0.0
    aging_lots = 0
    low_stock = 0
    coa_risk = 0
    for row in inventory:
        weight = _to_float(row.get("available_weight_g"))
        total_weight += max(weight, 0)
        if _to_float(row.get("days_since_received")) > 30:
            aging_lots += 1
        if 0 < weight < 500:
            low_stock += 1
        coa_status = str(row.get("coa_status") or "").lower()
        if coa_status in {"pending", "failed"}:
            coa_risk += 1

    return (
        f"Extraction inventory includes {len(inventory)} lots totaling {total_weight:,.0f}g. "
        f"Aging lots (>30 days): {aging_lots}. Low-stock lots: {low_stock}. COA watchouts: {coa_risk}."
    )


def interpret_projected_output(context: dict) -> str:
    """Interpret dashboard-provided projected output against targets without recalculation."""
    projected = _to_float(context.get("projected_output"), default=-1)
    target = _to_float(context.get("output_target"), default=-1)
    if projected < 0:
        return "Projected output data is not available in current context."
    if target < 0:
        return f"Projected output potential: {projected:,.0f} units. Target not provided for direct comparison."

    gap = projected - target
    if gap < 0:
        return f"Production is trending below target by {abs(gap):,.0f} units (projection {projected:,.0f} vs target {target:,.0f})."
    return f"On track to meet production targets (projection {projected:,.0f} vs target {target:,.0f})."


def prioritize_extraction_actions(context: dict) -> list[str]:
    """Generate prioritized extraction actions from the highest-risk operational signals."""
    actions: list[str] = []
    if context.get("failed_batches", 0) or context.get("held_batches", 0):
        actions.append("Resolve failed/held batches with QA before scheduling additional runs")
    if context.get("critical_alert_count", 0):
        actions.append("Triage critical equipment alerts immediately to protect throughput")
    if context.get("aging_lots", 0):
        actions.append("Prioritize aging lots nearing quality cutoff in the next production cycle")
    if context.get("low_available_stock", 0):
        actions.append("Replenish low input materials to avoid production gaps")
    if context.get("operator_variance_count", 0):
        actions.append("Coach operators with yield variance greater than 10% from team baseline")
    if context.get("maintenance_due", 0):
        actions.append("Schedule preventive maintenance on constrained extraction assets")
    if context.get("optimization_opportunities", 0):
        actions.append("Run optimization experiments on top-performing methods to lock in yield gains")
    if not actions:
        actions.append("Maintain current extraction cadence and monitor next run cycle for variance")
    return actions
