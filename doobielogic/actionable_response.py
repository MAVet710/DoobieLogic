from __future__ import annotations

from typing import Any


def _clean_items(values: list[Any] | None, limit: int = 8) -> list[str]:
    return [str(value).strip() for value in (values or []) if str(value).strip()][:limit]


def format_actionable_fallback(result: dict[str, Any]) -> dict[str, Any]:
    """Expose useful actions in the main answer when no conversational model is available."""

    formatted = dict(result)
    answer = str(formatted.get("answer") or "").strip()
    if not answer:
        answer = "I need more operating context to answer responsibly."
    if "**What to do" in answer or formatted.get("needs_clarification"):
        formatted["answer"] = answer
        formatted["response_contract_version"] = "actionable-v1"
        return formatted

    recommendations = _clean_items(formatted.get("recommendations"))
    risks = _clean_items(formatted.get("risk_flags"), limit=4)
    parts = [answer]
    if recommendations:
        parts.append("**What to do now**\n" + "\n".join(f"{index}. {item}" for index, item in enumerate(recommendations, 1)))
    else:
        parts.append(
            "**To make this actionable**\n"
            "Share the jurisdiction, license type, operating goal, and the records or measurements behind the question."
        )
    if risks:
        parts.append("**Do not miss**\n" + "\n".join(f"- {item}" for item in risks))
    if recommendations and str(formatted.get("confidence") or "").casefold() == "low":
        parts.append("**To make this facility-specific**\nProvide the jurisdiction, license type, time window, and source records behind the decision.")
    formatted["answer"] = "\n\n".join(parts)
    formatted["response_contract_version"] = "actionable-v1"
    return formatted
