from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TrustLevel = Literal["high", "medium"]
EntryType = Literal["regulator", "operations", "science", "retail", "safety", "tracking"]


@dataclass(frozen=True)
class SourceEntry:
    state: str | None
    module: str
    topic: str
    title: str
    summary: str
    source_url: str
    trust_level: TrustLevel
    entry_type: EntryType
    keywords: tuple[str, ...]


CURATED_SOURCE_PACK: tuple[SourceEntry, ...] = (
    SourceEntry("MA", "compliance", "program authority", "Massachusetts Cannabis Control Commission", "Primary Massachusetts regulator source for licensing, operations, guidance, and program updates.", "https://masscannabiscontrol.com/", "high", "regulator", ("massachusetts", "ma", "ccc", "compliance", "retail", "guidance")),
    SourceEntry("MA", "compliance", "statutes", "Massachusetts Legislature", "Massachusetts statutes and legislative materials used to verify legal references.", "https://malegislature.gov/", "high", "regulator", ("massachusetts", "ma", "law", "statute", "legislature")),
    SourceEntry("MA", "tracking", "seed-to-sale", "METRC", "Seed-to-sale platform reference used in regulated cannabis operations for package IDs, manifests, and reconciliation.", "https://www.metrc.com/", "medium", "tracking", ("metrc", "manifest", "package id", "seed-to-sale", "tracking")),
    SourceEntry("NJ", "compliance", "program authority", "New Jersey Cannabis Regulatory Commission", "Primary New Jersey regulator source for adult-use and medicinal cannabis guidance.", "https://www.nj.gov/cannabis/", "high", "regulator", ("new jersey", "nj", "crc", "compliance", "labeling")),
    SourceEntry("NY", "compliance", "program authority", "New York Office of Cannabis Management", "Primary New York regulator source for licensing, compliance, and operational guidance.", "https://cannabis.ny.gov/", "high", "regulator", ("new york", "ny", "ocm", "compliance", "packaging")),
    SourceEntry("CA", "compliance", "program authority", "California Department of Cannabis Control", "Primary California cannabis regulator source for licensing and compliance guidance.", "https://cannabis.ca.gov/", "high", "regulator", ("california", "ca", "dcc", "compliance", "testing", "packaging")),
    SourceEntry("PA", "compliance", "program authority", "Pennsylvania Medical Marijuana Program", "Primary Pennsylvania medical cannabis program source.", "https://www.pa.gov/agencies/health/programs/medical-marijuana.html", "high", "regulator", ("pennsylvania", "pa", "medical", "program")),
    SourceEntry("ME", "compliance", "program authority", "Maine Office of Cannabis Policy", "Primary Maine cannabis policy and licensing source.", "https://www.maine.gov/dafs/ocp/cannabis", "high", "regulator", ("maine", "me", "policy", "compliance", "tracking")),
    SourceEntry(None, "science", "cannabinoids", "National Library of Medicine", "Reference source for cannabinoid, terpene, and clinical literature background.", "https://www.ncbi.nlm.nih.gov/", "high", "science", ("thc", "cbd", "cbg", "terpene", "myrcene", "limonene", "pinene", "study")),
    SourceEntry(None, "safety", "public health", "CDC Cannabis Information", "Public health source for cannabis safety, impairment, and consumer education guidance.", "https://www.cdc.gov/cannabis/", "high", "safety", ("safety", "dose", "edibles", "onset", "consumer", "public health")),
    SourceEntry(None, "operations", "food safety", "FDA Food Guidance", "Reference source for GMP-style food safety concepts relevant to cannabis kitchens and co-manufacturing operations.", "https://www.fda.gov/food", "high", "operations", ("gmp", "kitchen", "sanitation", "allergen", "food safety", "quality agreement")),
    SourceEntry(None, "operations", "cultivation safety", "EPA", "Reference source for environmental and pest-management concepts relevant to cultivation operations.", "https://www.epa.gov/", "high", "operations", ("ipm", "pest", "cultivation", "environmental", "facility")),
    SourceEntry(None, "operations", "standards", "ASTM International", "Reference standards organization relevant to cannabis testing, processing, and operational quality systems.", "https://www.astm.org/", "medium", "operations", ("astm", "testing", "solvent", "dry cure", "homogeneity", "quality")),
    SourceEntry(None, "retail", "open-to-buy", "Shopify Retail Open-to-Buy Guide", "General retail planning reference for open-to-buy inventory control concepts.", "https://www.shopify.com/retail/open-to-buy", "medium", "retail", ("open-to-buy", "otb", "inventory", "budget", "buying")),
    SourceEntry(None, "retail", "industry association", "National Retail Federation", "General retail strategy reference for assortment and merchandising concepts.", "https://www.nrf.com/", "medium", "retail", ("assortment", "merchandising", "retail strategy", "category")),
    SourceEntry(None, "retail", "vendor management", "NACDS", "General retail and supply chain reference for scorecards and vendor-performance thinking.", "https://www.nacds.org/", "medium", "retail", ("vendor", "scorecard", "fill rate", "supply chain")),
)


def match_sources(question: str, state: str | None = None, module: str | None = None, limit: int = 6) -> list[SourceEntry]:
    q = question.lower()
    scored: list[tuple[int, SourceEntry]] = []
    for entry in CURATED_SOURCE_PACK:
        if state and entry.state not in {None, state.upper()}:
            continue
        if module and entry.module != module:
            continue
        score = 0
        if state and entry.state == state.upper():
            score += 3
        for kw in entry.keywords:
            if kw in q:
                score += 2
        if entry.topic in q:
            score += 1
        if entry.module in q:
            score += 1
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda item: (item[0], 1 if item[1].trust_level == "high" else 0), reverse=True)
    return [entry for _, entry in scored[:limit]]


def build_grounded_summary(question: str, state: str | None = None, module: str | None = None, limit: int = 6) -> dict:
    matches = match_sources(question=question, state=state, module=module, limit=limit)
    if not matches:
        return {
            "answer": "I do not have a direct curated source match for that yet. Use the existing analytics tools or add a source-backed entry before treating this as authoritative.",
            "sources": [],
            "confidence": "low",
            "grounding": "No curated source match",
        }

    top = matches[:3]
    lines = [f"- {entry.title}: {entry.summary}" for entry in top]
    confidence = "high" if any(entry.trust_level == "high" for entry in top) else "medium"
    grounding = "Curated static source pack"
    return {
        "answer": "\n".join(lines),
        "sources": [entry.source_url for entry in matches],
        "confidence": confidence,
        "grounding": grounding,
        "matches": [entry.__dict__ for entry in matches],
    }
