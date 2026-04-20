from __future__ import annotations


def analyze_dosage_control(data: dict) -> dict:
    variance = [float(x) for x in data.get("dosage_variance_pct", []) if x not in (None, "")]
    qc = [float(x) for x in data.get("qc_pass_rate", []) if x not in (None, "")]
    if not variance and not qc:
        return {"status": "skipped", "reason": "dosage/qc fields missing"}
    return {"status": "ok", "avg_dosage_variance_pct": round(sum(variance) / len(variance), 2) if variance else 0, "low_qc_rows": sum(1 for q in qc if q < 0.9)}


def analyze_kitchen_throughput(data: dict) -> dict:
    hours = [float(x) for x in data.get("production_hours", []) if x not in (None, "")]
    if not hours:
        return {"status": "skipped", "reason": "production_hours missing"}
    return {"status": "ok", "avg_production_hours": round(sum(hours) / len(hours), 2)}


def flag_kitchen_risk_signals(data: dict) -> dict:
    return {
        "status": "ok",
        "rework_batches": sum(1 for x in data.get("rework_flag", []) if bool(x)),
        "hold_batches": sum(1 for x in data.get("hold_flag", []) if bool(x)),
        "packaging_delays": sum(1 for x in data.get("packaging_delay_flag", []) if bool(x)),
        "sanitation_flags": sum(1 for x in data.get("sanitation_gap_flag", []) if bool(x)),
        "changeover_flags": sum(1 for x in data.get("allergen_changeover_flag", []) if bool(x)),
    }


def build_kitchen_action_plan(data: dict) -> dict:
    d = analyze_dosage_control(data)
    t = analyze_kitchen_throughput(data)
    r = flag_kitchen_risk_signals(data)
    actions = []
    if d.get("avg_dosage_variance_pct", 0) > 8:
        actions.append("Tighten dosage control checks on high-variance runs.")
    if r.get("sanitation_flags", 0) + r.get("changeover_flags", 0) > 0:
        actions.append("Escalate sanitation/changeover discipline on flagged batches.")
    if r.get("packaging_delays", 0) > 0:
        actions.append("Review kitchen-to-packaging handoff timing.")
    if not actions:
        actions.append("Kitchen signals stable; continue QC cadence.")
    return {"dosage_control": d, "throughput": t, "risk_signals": r, "actions": actions}


def render_kitchen_action_plan(summary: dict) -> str:
    return "\n".join(["Kitchen action plan:"] + [f"- {a}" for a in summary.get("actions", [])])
