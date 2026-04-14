from __future__ import annotations

from typing import Any


def analyze_science(data: dict[str, Any]) -> dict:
    temps = [float(x) for x in data.get("extraction_temperature_c", []) if x is not None]
    purge = [float(x) for x in data.get("purge_temperature_c", []) if x is not None]

    findings = []

    if temps:
        avg_temp = sum(temps) / len(temps)
        if avg_temp > 40:
            findings.append("Extraction temp may be degrading terpenes")

    if purge:
        avg_purge = sum(purge) / len(purge)
        if avg_purge > 38:
            findings.append("Purge temp may be too aggressive")

    if not findings:
        findings.append("No major chemistry risks detected")

    return {
        "status": "ok",
        "findings": findings,
        "confidence": "medium"
    }
