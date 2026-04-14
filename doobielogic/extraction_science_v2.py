from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExtractionScienceFinding:
    signal: str
    severity: str
    title: str
    detail: str
    recommendation: str


def _as_float_list(data: dict[str, Any], key: str) -> list[float]:
    raw = data.get(key, []) or []
    values: list[float] = []
    for item in raw:
        try:
            values.append(float(item))
        except (TypeError, ValueError):
            continue
    return values


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def analyze_terpene_preservation(data: dict[str, Any]) -> list[ExtractionScienceFinding]:
    findings: list[ExtractionScienceFinding] = []
    extraction_temp = _avg(_as_float_list(data, "extraction_temperature_c"))
    purge_temp = _avg(_as_float_list(data, "purge_temperature_c"))
    if extraction_temp is not None and extraction_temp > 40:
        findings.append(
            ExtractionScienceFinding(
                signal="terpene_preservation_risk",
                severity="medium",
                title="Extraction temperature may be too terpene-aggressive",
                detail=f"Average extraction temperature is {extraction_temp:.1f}°C. Elevated temperatures can reduce preservation of lighter volatiles.",
                recommendation="Lower extraction temperature or shift to terpene-first fractionation when aroma retention matters.",
            )
        )
    if purge_temp is not None and purge_temp > 38:
        findings.append(
            ExtractionScienceFinding(
                signal="purge_terpene_loss_risk",
                severity="medium",
                title="Purge settings may be stripping desirable volatiles",
                detail=f"Average purge temperature is {purge_temp:.1f}°C. Excessive post-process heat can flatten terpene expression even when potency remains acceptable.",
                recommendation="Review purge temperature and time together. Use the lowest effective thermal input that still clears release targets.",
            )
        )
    return findings


def analyze_decarb_conversion(data: dict[str, Any]) -> list[ExtractionScienceFinding]:
    findings: list[ExtractionScienceFinding] = []
    decarb_temps = _as_float_list(data, "decarb_temperature_c")
    decarb_times = _as_float_list(data, "decarb_time_min")
    temp = _avg(decarb_temps)
    time = _avg(decarb_times)
    if temp is None and time is None:
        return findings

    if temp is not None and temp >= 145:
        findings.append(
            ExtractionScienceFinding(
                signal="decarb_overconversion_risk",
                severity="high",
                title="Decarb program may be overdriving conversion",
                detail=f"Average decarb temperature is {temp:.1f}°C, which can increase degradation risk if time is not tightly controlled.",
                recommendation="Tighten decarb control and verify target acid-to-neutral ratios through post-process potency review.",
            )
        )
    elif temp is not None and temp < 95:
        findings.append(
            ExtractionScienceFinding(
                signal="decarb_underconversion_risk",
                severity="medium",
                title="Decarb program may be too soft for target conversion",
                detail=f"Average decarb temperature is {temp:.1f}°C. Incomplete conversion can leave potency stranded in acidic form when neutral output is expected.",
                recommendation="Confirm whether the intended product spec requires neutral cannabinoids and increase thermal input only if chemistry targets are missed.",
            )
        )

    if time is not None and time > 120:
        findings.append(
            ExtractionScienceFinding(
                signal="decarb_time_excessive",
                severity="medium",
                title="Decarb residence time looks long",
                detail=f"Average decarb time is {time:.1f} minutes. Extended residence time can increase oxidation or flavor flattening even when conversion succeeds.",
                recommendation="Check whether shorter time at controlled temperature reaches the same conversion endpoint with less degradation pressure.",
            )
        )
    return findings


def analyze_purge_sufficiency(data: dict[str, Any]) -> list[ExtractionScienceFinding]:
    findings: list[ExtractionScienceFinding] = []
    purge_time = _avg(_as_float_list(data, "purge_time_hr"))
    vacuum = _avg(_as_float_list(data, "vacuum_level"))
    solvent_flags = sum(1 for x in (data.get("residual_solvent_flag", []) or []) if bool(x))

    if solvent_flags > 0:
        findings.append(
            ExtractionScienceFinding(
                signal="residual_solvent_release_risk",
                severity="high",
                title="Residual solvent flags detected",
                detail=f"There are {solvent_flags} flagged run(s) indicating potential release risk tied to purge sufficiency or solvent recovery.",
                recommendation="Hold release on flagged lots until residual solvent results and purge conditions are reviewed together.",
            )
        )
    if purge_time is not None and purge_time < 6:
        findings.append(
            ExtractionScienceFinding(
                signal="short_purge_window",
                severity="medium",
                title="Purge window may be short",
                detail=f"Average purge time is {purge_time:.1f} hours. That may be insufficient for heavier hydrocarbon loading or higher-mass batches.",
                recommendation="Benchmark purge time by batch mass, solvent system, and final texture instead of using one static dwell time.",
            )
        )
    if vacuum is not None and vacuum > -25:
        findings.append(
            ExtractionScienceFinding(
                signal="weak_vacuum",
                severity="medium",
                title="Vacuum conditions may be too weak",
                detail=f"Average vacuum level is {vacuum:.1f}. Weak vacuum reduces solvent removal efficiency during purge and can drag out cycle time.",
                recommendation="Inspect vacuum integrity, pump performance, and leak control before increasing thermal load.",
            )
        )
    return findings


def analyze_release_readiness(data: dict[str, Any]) -> list[ExtractionScienceFinding]:
    findings: list[ExtractionScienceFinding] = []
    qa_holds = sum(1 for x in (data.get("qa_hold", []) or []) if bool(x))
    coa_values = [str(x).strip().lower() for x in (data.get("coa_status", []) or []) if x is not None]
    failed = sum(1 for x in coa_values if x == "failed")
    pending = sum(1 for x in coa_values if x == "pending")

    if failed > 0:
        findings.append(
            ExtractionScienceFinding(
                signal="failed_coa_batches",
                severity="high",
                title="Failed COA batches are blocking release confidence",
                detail=f"There are {failed} failed batch(es) in the current extraction dataset.",
                recommendation="Separate root-cause review by failure type: residual solvent, pesticides, metals, microbial, or potency variance.",
            )
        )
    if pending > 0:
        findings.append(
            ExtractionScienceFinding(
                signal="pending_release_queue",
                severity="medium",
                title="Pending COAs are creating release uncertainty",
                detail=f"There are {pending} batch(es) still pending certificate results.",
                recommendation="Prioritize batches by promised completion date, customer commitments, and value at risk.",
            )
        )
    if qa_holds > 0:
        findings.append(
            ExtractionScienceFinding(
                signal="qa_hold_pressure",
                severity="high",
                title="QA holds are suppressing release readiness",
                detail=f"There are {qa_holds} batch(es) under QA hold.",
                recommendation="Use hold reason codes and close them with documented disposition before scheduling downstream packaging or transfer.",
            )
        )
    return findings


def build_extraction_science_summary(data: dict[str, Any]) -> dict[str, Any]:
    findings: list[ExtractionScienceFinding] = []
    for analyzer in (
        analyze_terpene_preservation,
        analyze_decarb_conversion,
        analyze_purge_sufficiency,
        analyze_release_readiness,
    ):
        findings.extend(analyzer(data))

    severity_rank = {"high": 3, "medium": 2, "low": 1}
    findings = sorted(findings, key=lambda x: severity_rank.get(x.severity, 0), reverse=True)

    return {
        "status": "ok",
        "finding_count": len(findings),
        "findings": [
            {
                "signal": f.signal,
                "severity": f.severity,
                "title": f.title,
                "detail": f.detail,
                "recommendation": f.recommendation,
            }
            for f in findings
        ],
        "top_recommendations": [f.recommendation for f in findings[:5]],
        "grounding": "Heuristic extraction-science reasoning layered on structured process data.",
        "confidence": "medium",
    }


def render_extraction_science_summary(summary: dict[str, Any]) -> str:
    if not summary or not summary.get("findings"):
        return "Extraction science layer: no scientist-grade findings from current inputs."
    lines = ["Extraction science layer:"]
    for finding in summary.get("findings", [])[:6]:
        lines.append(f"- [{finding['severity'].upper()}] {finding['title']}: {finding['detail']}")
    return "\n".join(lines)
