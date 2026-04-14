from __future__ import annotations

from typing import Any

from doobielogic.learning_store_v1 import summarize_learning


def apply_learning_bias(*, mode: str, recommendations: list[str], confidence: str) -> dict[str, Any]:
    learning = summarize_learning(mode)
    bias = learning.get("confidence_bias", "flat")
    recs = list(recommendations or [])

    prioritized: list[str] = []
    if bias == "up":
        prioritized.extend(recs[:5])
        confidence_out = "high" if confidence in {"medium", "high"} else "medium"
    elif bias == "down":
        prioritized.extend(recs[:3])
        prioritized.append("Review prior rejected recommendations before acting aggressively.")
        confidence_out = "medium" if confidence == "high" else "low"
    else:
        prioritized.extend(recs[:5])
        confidence_out = confidence

    return {
        "recommendations": prioritized,
        "confidence": confidence_out,
        "learning_summary": learning,
        "optimization_note": f"Learning bias is {bias}. Recommendation intensity adjusted accordingly.",
    }
