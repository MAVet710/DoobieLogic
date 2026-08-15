from __future__ import annotations

from typing import Any

from doobielogic.jurisdictions import infer_jurisdiction_code


LEGAL_INTENT_TERMS = (
    "jurisdiction",
    "state-specific",
    "state specific",
    "state rule",
    "legal requirement",
    "legally required",
    "compliant",
    "compliance",
    "purchase limit",
    "possession limit",
    "can we legally",
    "are we allowed",
)

REGULATED_TOPIC_TERMS = (
    "packaging",
    "label",
    "advertising",
    "marketing",
    "transport",
    "delivery",
    "manifest",
    "testing",
    "sample",
    "security",
    "camera",
    "waste",
    "recall",
    "sale",
    "purchase",
    "dispensary",
    "cultivation",
    "manufacturing",
)

LICENSE_CONTEXTS = (
    ("retail dispensary", ("dispensary", "budtender", "retail store", "point of sale", "pos")),
    ("cultivation", ("cultivation", "grow", "canopy", "harvest", "flower room", "veg room")),
    ("manufacturing", ("manufacturing", "processor", "kitchen", "edible", "infusion", "packaging line")),
    ("extraction", ("extraction", "hydrocarbon", "solvent", "distillate", "rosin")),
    ("testing laboratory", ("laboratory", "lab result", "oos", "sampling plan", "coa")),
    ("distribution", ("distribution", "wholesale", "delivery route", "manifest", "shipment")),
)


def requires_jurisdiction(question: str, mode: str | None = None) -> bool:
    text = str(question or "").strip().casefold()
    if str(mode or "").casefold() == "compliance":
        return True
    if any(term in text for term in LEGAL_INTENT_TERMS):
        return True
    return "required" in text and any(term in text for term in REGULATED_TOPIC_TERMS)


def infer_state_from_history(history: list[dict[str, Any]] | None) -> str | None:
    for item in reversed(history or []):
        content = item.get("content")
        if content is None and isinstance(item.get("result"), dict):
            context = item["result"].get("compliance_context") or {}
            code = str(context.get("code") or "").strip().upper()
            if code:
                return code
            content = item["result"].get("answer")
        if code := infer_jurisdiction_code(str(content or "")):
            return code
    return None


def infer_license_context(question: str, history: list[dict[str, Any]] | None = None) -> str | None:
    parts = [str(question or "")]
    for item in (history or [])[-8:]:
        if str(item.get("role") or "").casefold() == "user":
            parts.append(str(item.get("content") or ""))
    text = " ".join(parts).casefold()
    for label, terms in LICENSE_CONTEXTS:
        if any(term in text for term in terms):
            return label
    return None


def infer_secondary_modes(question: str, primary_mode: str) -> list[str]:
    modes: list[str] = []
    if primary_mode != "compliance" and requires_jurisdiction(question, primary_mode):
        modes.append("compliance")
    text = str(question or "").casefold()
    if primary_mode not in {"quality", "laboratory"} and any(term in text for term in ("release", "quarantine", "recall", "complaint")):
        modes.append("quality")
    return list(dict.fromkeys(modes))


def jurisdiction_clarification_result(
    question: str,
    route_label: str,
    base_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = dict(base_result or {})
    baseline = str(base.get("answer") or "").strip()
    text = str(question or "").casefold()
    missing_context = ["jurisdiction"]
    if not any(term in text for term in ("adult use", "adult-use", "medical", "dispensary", "cultivator", "manufacturer", "laboratory", "distributor")):
        missing_context.append("license_type")
    if missing_context == ["jurisdiction"]:
        answer = (
            "Which state or U.S. territory are you operating in? "
            "I need that detail to verify the current requirement instead of giving you a generic or potentially outdated rule."
        )
    else:
        answer = (
            "Which U.S. state or territory and license type are you operating under? "
            "I need those two details to verify the current requirements instead of giving you a generic or potentially outdated rule."
        )
    if baseline:
        answer += f"\n\n**Universal operating baseline while I verify the jurisdiction:**\n\n{baseline}"
    recommendations = list(base.get("recommendations") or [])
    if not recommendations:
        recommendations = [
            "Reply with the state or territory.",
            "Identify the license type and activity involved.",
            "Share the product, transaction, or process facts that could change the rule.",
        ]
    base.update(
        {
            "answer": answer,
            "recommendations": recommendations,
            "confidence": "low",
            "route_label": route_label,
            "needs_clarification": True,
            "missing_context": missing_context,
            "rule_verified": False,
            "question": question,
        }
    )
    return base


def build_conversation_profile(
    question: str,
    *,
    state: str | None,
    primary_mode: str,
    history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    resolved_state = state or infer_jurisdiction_code(question) or infer_state_from_history(history)
    return {
        "jurisdiction": resolved_state,
        "license_context": infer_license_context(question, history),
        "primary_domain": primary_mode,
        "secondary_domains": infer_secondary_modes(question, primary_mode),
        "jurisdiction_required": requires_jurisdiction(question, primary_mode),
    }
