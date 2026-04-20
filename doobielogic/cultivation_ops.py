from __future__ import annotations


def analyze_room_performance(data: dict) -> dict:
    rooms = data.get("room", [])
    actual = data.get("actual_yield_g", [])
    expected = data.get("expected_yield_g", [])
    if not rooms or not actual:
        return {"status": "skipped", "reason": "room/yield missing"}
    perf: dict[str, list[float]] = {}
    for idx, room in enumerate(rooms):
        if idx >= len(actual):
            continue
        try:
            current_actual = float(actual[idx])
            current_expected = float(expected[idx]) if idx < len(expected) else 0.0
        except (TypeError, ValueError):
            continue
        gap = current_actual - current_expected if idx < len(expected) else current_actual
        perf.setdefault(str(room), []).append(gap)
    avg_gap = {room: round(sum(vals) / len(vals), 2) for room, vals in perf.items()}
    under = [room for room, gap in avg_gap.items() if gap < 0]
    return {"status": "ok", "avg_gap_by_room": avg_gap, "underperforming_rooms": under}


def analyze_yield_variance(data: dict) -> dict:
    expected = [float(x) for x in data.get("expected_yield_g", []) if x not in (None, "")]
    actual = [float(x) for x in data.get("actual_yield_g", []) if x not in (None, "")]
    if not expected or not actual:
        return {"status": "skipped", "reason": "yield fields missing"}
    diffs = [a - e for a, e in zip(actual, expected)]
    variance = max(diffs) - min(diffs) if diffs else 0
    return {"status": "ok", "yield_gap_range_g": round(variance, 2), "avg_gap_g": round(sum(diffs) / len(diffs), 2)}


def flag_cultivation_risk_signals(data: dict) -> dict:
    moisture = sum(1 for x in data.get("moisture_risk_flag", []) if bool(x))
    microbial = sum(1 for x in data.get("microbial_risk_flag", []) if bool(x))
    waste = [float(x) for x in data.get("waste_g", []) if x is not None]
    cycle = [float(x) for x in data.get("cycle_days", []) if x is not None]
    pass_rate = [float(x) for x in data.get("test_pass_rate", []) if x is not None]
    return {
        "status": "ok",
        "moisture_flags": moisture,
        "microbial_flags": microbial,
        "high_waste_rows": sum(1 for w in waste if w > (sum(waste) / len(waste) if waste else 0)),
        "cycle_outliers": sum(1 for c in cycle if c > (sum(cycle) / len(cycle) if cycle else 0) * 1.15),
        "unstable_pass_rows": sum(1 for p in pass_rate if p < 0.9),
    }


def build_cultivation_action_plan(data: dict) -> dict:
    room = analyze_room_performance(data)
    risk = flag_cultivation_risk_signals(data)
    actions = []
    if room.get("underperforming_rooms"):
        actions.append(f"Stabilize underperforming rooms: {room['underperforming_rooms']}")
    if risk.get("microbial_flags", 0) > 0 or risk.get("moisture_flags", 0) > 0:
        actions.append("Escalate moisture/microbial checkpoints and sanitation control.")
    if risk.get("high_waste_rows", 0) > 0:
        actions.append("Run waste root-cause review by room and strain.")
    if not actions:
        actions.append("No severe cultivation signals; maintain monitoring cadence.")
    return {"room_performance": room, "risk_signals": risk, "actions": actions}


def render_cultivation_action_plan(summary: dict) -> str:
    return "\n".join(["Cultivation action plan:"] + [f"- {a}" for a in summary.get("actions", [])])
