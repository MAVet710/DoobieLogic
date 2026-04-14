from __future__ import annotations

from typing import Any


def inject_commercial_context(data: dict[str, Any], store_id: str | None = None) -> dict[str, Any]:
    return {
        "store_id": store_id or "default",
        "dataset_size": len(data or {}),
        "multi_store_ready": True,
        "note": "Commercial context applied"
    }


def format_commercial_output(base: dict[str, Any], store_id: str | None = None) -> dict[str, Any]:
    return {
        "store_id": store_id or "default",
        "answer": base.get("answer"),
        "recommendations": base.get("recommendations", []),
        "confidence": base.get("confidence"),
        "commercial_ready": True
    }
