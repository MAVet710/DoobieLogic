from __future__ import annotations


def analyze_packaging_efficiency(data: dict) -> dict:
    completion = [float(x) for x in data.get("completion_rate", []) if x is not None]
    hours = [float(x) for x in data.get("packaging_hours", []) if x is not None]
    if not completion and not hours:
        return {"status": "skipped", "reason": "completion/hours missing"}
    return {"status": "ok", "avg_completion_rate": round(sum(completion) / len(completion), 3) if completion else 0, "avg_packaging_hours": round(sum(hours) / len(hours), 2) if hours else 0}


def flag_packaging_risk_signals(data: dict) -> dict:
    recon = [abs(float(x)) for x in data.get("reconciliation_variance", []) if x is not None]
    scrap = [float(x) for x in data.get("scrap_units", []) if x is not None]
    return {
        "status": "ok",
        "label_errors": sum(1 for x in data.get("label_error_flag", []) if bool(x)),
        "holds": sum(1 for x in data.get("packaging_hold_flag", []) if bool(x)),
        "rework": sum(1 for x in data.get("rework_flag", []) if bool(x)),
        "high_reconciliation_rows": sum(1 for x in recon if x > 2),
        "high_scrap_rows": sum(1 for x in scrap if x > (sum(scrap) / len(scrap) if scrap else 0)),
    }


def build_packaging_action_plan(data: dict) -> dict:
    e = analyze_packaging_efficiency(data)
    r = flag_packaging_risk_signals(data)
    actions = []
    if r.get("label_errors", 0) > 0:
        actions.append("Escalate recurring label errors by SKU and shift.")
    if r.get("high_reconciliation_rows", 0) > 0:
        actions.append("Investigate reconciliation variance spikes by line.")
    if e.get("avg_completion_rate", 1) < 0.9:
        actions.append("Address low completion rates via line balancing and coaching.")
    if not actions:
        actions.append("Packaging performance stable; maintain line checks.")
    return {"efficiency": e, "risk_signals": r, "actions": actions}


def render_packaging_action_plan(summary: dict) -> str:
    return "\n".join(["Packaging action plan:"] + [f"- {a}" for a in summary.get("actions", [])])
