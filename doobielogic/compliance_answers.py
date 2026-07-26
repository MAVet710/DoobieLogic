from __future__ import annotations

from dataclasses import dataclass
import re

from doobielogic.jurisdictions import get_jurisdiction_context


@dataclass(frozen=True)
class AdultUsePurchaseLimit:
    jurisdiction_code: str
    effective_date: str
    flower_limit: str
    concentrate_limit: str
    edible_limit: str
    summary: str
    authority_title: str
    authority_url: str


# Exact operational rules are added only after review of a current, primary
# regulator or government source. This is intentionally separate from the
# broader jurisdiction registry so an entry-point link is never mistaken for
# verified rule text.
ADULT_USE_PURCHASE_LIMITS: dict[str, AdultUsePurchaseLimit] = {
    "MA": AdultUsePurchaseLimit(
        jurisdiction_code="MA",
        effective_date="2026-04-19",
        flower_limit="2 ounces of marijuana flower",
        concentrate_limit="10 grams of active THC in marijuana concentrate, including tinctures",
        edible_limit="1,000 milligrams of active THC in edibles",
        summary=(
            "A Massachusetts adult-use retailer may not knowingly sell more than two ounces of "
            "marijuana—or its combined dry-weight equivalent—to one customer per day. The same "
            "two-ounce limit applies per transaction."
        ),
        authority_title=(
            "Massachusetts Cannabis Control Commission Administrative Order No. 6 "
            "(effective April 19, 2026)"
        ),
        authority_url=(
            "https://masscannabiscontrol.com/2026/04/"
            "administrative-order-relative-to-equivalency-and-conversion-standards-for-"
            "marijuana-products-april-19-2026/"
        ),
    ),
}


_PURCHASE_LIMIT_PATTERN = re.compile(
    r"\b(?:purchase|purchasing|buy|buying|sale|sales|transaction|daily)\b.*"
    r"\b(?:limit|maximum|max|amount|how much|adult[\s-]?use)\b|"
    r"\b(?:limit|maximum|max|amount|how much|adult[\s-]?use)\b.*"
    r"\b(?:purchase|purchasing|buy|buying|sale|sales|transaction|daily)\b",
    re.IGNORECASE,
)


def answer_verified_compliance_question(question: str, state: str | None) -> dict | None:
    """Answer supported purchase-limit questions from verified primary-source records."""

    code = str(state or "").strip().upper()
    rule = ADULT_USE_PURCHASE_LIMITS.get(code)
    if rule is None or not _PURCHASE_LIMIT_PATTERN.search(str(question or "")):
        return None
    context = get_jurisdiction_context(code)
    return {
        "answer": (
            f"As of {rule.effective_date}, the Massachusetts adult-use daily purchase limit is "
            f"**{rule.flower_limit}**, or the combined equivalent: **{rule.concentrate_limit}** "
            f"or **{rule.edible_limit}**. The limit is also two ounces or its equivalent per transaction."
        ),
        "explanation": (
            f"{rule.summary} Mixed-product purchases must stay within the combined equivalency limit; "
            "the listed quantities are alternatives, not amounts that can each be purchased on top of one another."
        ),
        "recommendations": [
            "Configure point-of-sale controls for the combined two-ounce equivalency limit.",
            "Use the Commission’s effective order as the controlling source and monitor later rulemaking.",
        ],
        "confidence": "high",
        "sources": [f"{rule.authority_title}: {rule.authority_url}"],
        "mode": "compliance",
        "risk_flags": [],
        "inefficiencies": [],
        "routed_mode": "compliance",
        "route_label": "Compliance",
        "routed_by": "Matched a verified jurisdiction rule",
        "needs_clarification": False,
        "missing_context": [],
        "compliance_context": context.to_dict() if context else None,
        "rule_effective_date": rule.effective_date,
        "rule_verified": True,
    }
