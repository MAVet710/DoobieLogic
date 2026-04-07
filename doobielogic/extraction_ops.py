from __future__ import annotations


def analyze_yield_performance(data: dict) -> dict:
    yields = [float(x) for x in data.get("yield_pct", []) if x is not None]
    if not yields:
        return {"status": "skipped", "reason": "yield_pct missing"}
    avg = sum(yields) / len(yields)
    weak = sum(1 for y in yields if y < avg * 0.8)
    return {"status": "ok", "avg_yield_pct": round(avg, 2), "weak_yield_batches": weak}


def analyze_throughput(data: dict) -> dict:
    turn = [float(x) for x in data.get("turnaround_hours", []) if x is not None]
    down = [float(x) for x in data.get("downtime_minutes", []) if x is not None]
    if not turn and not down:
        return {"status": "skipped", "reason": "throughput fields missing"}
    return {"status": "ok", "avg_turnaround_hours": round(sum(turn) / len(turn), 2) if turn else 0, "avg_downtime_minutes": round(sum(down) / len(down), 2) if down else 0}


def flag_extraction_risk_signals(data: dict) -> dict:
    failed = sum(1 for x in data.get("pass_fail", []) if str(x).lower() == "fail")
    flagged = sum(1 for x in data.get("residual_solvent_flag", []) if bool(x))
    rework = sum(1 for x in data.get("rework_flag", []) if bool(x))
    return {"status": "ok", "failed_batches": failed, "residual_flags": flagged, "rework_batches": rework}


def build_extraction_action_plan(data: dict) -> dict:
    y = analyze_yield_performance(data)
    t = analyze_throughput(data)
    r = flag_extraction_risk_signals(data)
    actions = []
    if y.get("weak_yield_batches", 0) > 0:
        actions.append("Investigate weak-yield batches by input material and output type.")
    if t.get("avg_downtime_minutes", 0) > 45:
        actions.append("Reduce downtime via line-level root cause and maintenance checks.")
    if r.get("failed_batches", 0) + r.get("rework_batches", 0) > 0:
        actions.append("Escalate failed/rework concentration with operator coaching and SOP audits.")
    if not actions:
        actions.append("Extraction metrics stable; maintain batch-level controls.")
    return {"yield_performance": y, "throughput": t, "risk_signals": r, "actions": actions}


def render_extraction_action_plan(summary: dict) -> str:
    return "\n".join(["Extraction action plan:"] + [f"- {a}" for a in summary.get("actions", [])])
