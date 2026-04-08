from __future__ import annotations

from doobielogic.regulations import REGULATION_LINKS


def analyze_issue_concentration(data: dict) -> dict:
    issues = [str(x) for x in data.get("issue_type", [])]
    depts = [str(x) for x in data.get("department", [])]
    if not issues:
        return {"status": "skipped", "reason": "issue_type missing"}
    issue_counts: dict[str, int] = {}
    dept_counts: dict[str, int] = {}
    for i in issues:
        issue_counts[i] = issue_counts.get(i, 0) + 1
    for d in depts:
        dept_counts[d] = dept_counts.get(d, 0) + 1
    return {"status": "ok", "top_issues": dict(sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]), "top_departments": dict(sorted(dept_counts.items(), key=lambda x: x[1], reverse=True)[:5]), "repeat_issue_count": sum(1 for x in data.get("repeat_issue_flag", []) if bool(x))}


def analyze_corrective_action_age(data: dict) -> dict:
    open_days = [float(x) for x in data.get("open_days", []) if x is not None]
    if not open_days:
        return {"status": "skipped", "reason": "open_days missing"}
    avg = sum(open_days) / len(open_days)
    aging = sum(1 for x in open_days if x > max(30, avg * 1.2))
    return {"status": "ok", "avg_open_days": round(avg, 2), "aging_actions": aging}


def build_compliance_action_plan(data: dict, state: str | None = None) -> dict:
    issues = analyze_issue_concentration(data)
    age = analyze_corrective_action_age(data)
    actions = []
    if issues.get("repeat_issue_count", 0) > 0:
        actions.append("Prioritize repeat issue categories with department owners.")
    if age.get("aging_actions", 0) > 0:
        actions.append("Escalate aging CAPAs and enforce closure cadence.")
    if sum(1 for x in data.get("training_gap_flag", []) if bool(x)) > 0:
        actions.append("Tie compliance remediation to targeted training plans.")
    if not actions:
        actions.append("No acute compliance pressure signal from file data.")

    state_code = (state or "").upper()
    refs = REGULATION_LINKS.get(state_code, {}) if state_code else {}
    return {
        "issue_concentration": issues,
        "corrective_action_age": age,
        "actions": actions,
        "grounded_references": refs,
        "legal_notice": "Operational guidance only; not legal advice.",
    }


def render_compliance_action_plan(summary: dict) -> str:
    lines = ["Compliance action plan:"]
    lines += [f"- {a}" for a in summary.get("actions", [])]
    lines.append(f"- Notice: {summary.get('legal_notice', 'Operational guidance only.')}")
    if summary.get("grounded_references"):
        lines.append(f"- State references: {summary['grounded_references']}")
    return "\n".join(lines)
