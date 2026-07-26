from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from doobielogic.regulations import REGULATION_LINKS


ProgramScope = Literal[
    "adult_use_and_medical",
    "adult_use_limited_market",
    "medical_only",
    "limited_medical",
    "no_comprehensive_program",
]

REGISTRY_REVIEWED_ON = "2026-07-25"

JURISDICTION_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
    "AS": "American Samoa",
    "GU": "Guam",
    "MP": "Northern Mariana Islands",
    "PR": "Puerto Rico",
    "VI": "U.S. Virgin Islands",
}

_ADULT_AND_MEDICAL = {
    "AK",
    "AZ",
    "CA",
    "CO",
    "CT",
    "DE",
    "IL",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MO",
    "MT",
    "NV",
    "NJ",
    "NM",
    "NY",
    "OH",
    "OR",
    "RI",
    "VT",
    "WA",
    "GU",
    "MP",
    "VI",
}
_ADULT_LIMITED = {"DC", "VA"}
_MEDICAL_ONLY = {
    "AL",
    "AR",
    "FL",
    "HI",
    "KY",
    "LA",
    "MS",
    "NE",
    "NH",
    "ND",
    "OK",
    "PA",
    "SD",
    "UT",
    "WV",
    "PR",
}
_LIMITED_MEDICAL = {"GA", "IA", "TX"}

PROGRAM_SCOPES: dict[str, ProgramScope] = {}
for _code in JURISDICTION_NAMES:
    if _code in _ADULT_AND_MEDICAL:
        PROGRAM_SCOPES[_code] = "adult_use_and_medical"
    elif _code in _ADULT_LIMITED:
        PROGRAM_SCOPES[_code] = "adult_use_limited_market"
    elif _code in _MEDICAL_ONLY:
        PROGRAM_SCOPES[_code] = "medical_only"
    elif _code in _LIMITED_MEDICAL:
        PROGRAM_SCOPES[_code] = "limited_medical"
    else:
        PROGRAM_SCOPES[_code] = "no_comprehensive_program"

SCOPE_LABELS = {
    "adult_use_and_medical": "Adult-use and medical",
    "adult_use_limited_market": "Adult-use possession and/or limited market plus medical",
    "medical_only": "Medical program only",
    "limited_medical": "Limited medical or low-THC program",
    "no_comprehensive_program": "No comprehensive state or territory cannabis program",
}


@dataclass(frozen=True)
class ComplianceSource:
    title: str
    url: str
    source_type: str
    last_reviewed: str


@dataclass(frozen=True)
class JurisdictionContext:
    code: str
    jurisdiction: str
    program_scope: ProgramScope
    scope_label: str
    sources: tuple[ComplianceSource, ...]
    confidence: str
    review_status: str
    last_updated: str
    rule_coverage: str
    actionable: bool
    caution: str

    def to_dict(self) -> dict:
        return asdict(self)


def get_jurisdiction_context(code: str | None) -> JurisdictionContext | None:
    safe_code = str(code or "").strip().upper()
    if safe_code not in JURISDICTION_NAMES:
        return None
    links = REGULATION_LINKS.get(safe_code, {})
    sources: list[ComplianceSource] = []
    if links.get("program"):
        sources.append(
            ComplianceSource(
                title=f"{JURISDICTION_NAMES[safe_code]} official cannabis program or government authority",
                url=links["program"],
                source_type="official_program",
                last_reviewed=REGISTRY_REVIEWED_ON,
            )
        )
    if links.get("statutes"):
        sources.append(
            ComplianceSource(
                title=f"{JURISDICTION_NAMES[safe_code]} official statutes or rules",
                url=links["statutes"],
                source_type="official_law_or_rules",
                last_reviewed=REGISTRY_REVIEWED_ON,
            )
        )
    scope = PROGRAM_SCOPES[safe_code]
    is_operating_program = scope != "no_comprehensive_program"
    return JurisdictionContext(
        code=safe_code,
        jurisdiction=JURISDICTION_NAMES[safe_code],
        program_scope=scope,
        scope_label=SCOPE_LABELS[scope],
        sources=tuple(sources),
        confidence="medium" if sources else "low",
        review_status=(
            "official-source entry points reviewed; exact current rule text must still be verified"
            if is_operating_program
            else "verify current law before assuming regulated cannabis activity is permitted"
        ),
        last_updated=REGISTRY_REVIEWED_ON,
        rule_coverage="official_source_registry_only",
        actionable=False,
        caution=(
            "Operational compliance guidance only. Confirm the current rule text, bulletins, "
            "local ordinances, and license conditions with the regulator or qualified counsel before action."
        ),
    )


def compliance_context_text(code: str | None) -> str:
    context = get_jurisdiction_context(code)
    if context is None:
        return (
            "Jurisdiction: not provided or unsupported\n"
            "Program scope: unknown\n"
            "Confidence: low\n"
            "Review status: A jurisdiction is required before compliance guidance can be treated as actionable."
        )
    source_lines = "\n".join(
        f"- {source.title}: {source.url} (reviewed {source.last_reviewed})"
        for source in context.sources
    )
    return (
        f"Jurisdiction: {context.jurisdiction} ({context.code})\n"
        f"Program scope: {context.scope_label}\n"
        f"Last updated: {context.last_updated}\n"
        f"Confidence: {context.confidence}\n"
        f"Review status: {context.review_status}\n"
        f"Rule coverage: {context.rule_coverage}\n"
        f"Actionable without verification: {'yes' if context.actionable else 'no'}\n"
        f"Official sources:\n{source_lines or '- No official source registered.'}\n"
        f"Caution: {context.caution}"
    )


def legal_jurisdiction_codes() -> tuple[str, ...]:
    return tuple(
        code
        for code in JURISDICTION_NAMES
        if PROGRAM_SCOPES[code] != "no_comprehensive_program"
    )
