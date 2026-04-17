from __future__ import annotations

from typing import Any


def evaluate_doobie_response(response: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    explanation = str(response.get("explanation") or "")
    answer = str(response.get("answer") or "")
    recommendations = response.get("recommendations") or []
    confidence = str(response.get("confidence") or "low").lower()

    checks = {
        "relevance": bool(answer.strip()) and bool(explanation.strip()),
        "hallucination_risk": "low" if response.get("sources") else "medium",
        "missing_logic": not (context.get("relevant_rules") and "rule" not in explanation.lower()),
        "weak_context_usage": "structured" not in explanation.lower() and "context" not in explanation.lower(),
    }

    failures: list[str] = []
    if not checks["relevance"]:
        failures.append("Missing answer/explanation relevance linkage.")
    if checks["hallucination_risk"] == "medium" and confidence in {"high", "medium"}:
        failures.append("Confidence may be overstated without source support.")
    if checks["missing_logic"]:
        failures.append("Response does not clearly connect to available logic/rules.")
    if checks["weak_context_usage"]:
        failures.append("Response does not clearly use structured context.")
    if not recommendations:
        failures.append("Recommendations are missing.")

    return {
        "pass": len(failures) == 0,
        "checks": checks,
        "failures": failures,
        "score": max(0, 100 - (len(failures) * 20)),
    }


def apply_low_confidence_fallback(response: dict[str, Any]) -> dict[str, Any]:
    confidence = str(response.get("confidence") or "low").lower()
    if confidence in {"high", "medium"}:
        return response

    safe = dict(response)
    safe["answer"] = "Insufficient confidence for a definitive recommendation."
    safe["explanation"] = (
        "A safe fallback response was returned because confidence is low. "
        "Please validate data completeness and request additional context."
    )
    safe["recommendations"] = [
        "Verify key KPIs and upload structured department data.",
        "Re-run request with clearer mode (buyer, inventory, extraction, ops).",
    ]
    safe["sources"] = response.get("sources") or []
    safe["confidence"] = "low"
    return safe
