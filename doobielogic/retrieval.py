from __future__ import annotations

from typing import Any

from doobielogic.jurisdictions import get_jurisdiction_context
from doobielogic.public_knowledge_v2 import query_public_knowledge_v2
from doobielogic.sourcepack import match_sources


def _record_view(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: record.get(key)
        for key in (
            "record_id",
            "state",
            "domain",
            "topic",
            "title",
            "summary",
            "source_url",
            "source_type",
            "trust_level",
            "update_cadence",
            "notes",
        )
        if record.get(key) not in (None, "")
    }


def build_retrieval_context(
    question: str,
    *,
    state: str | None,
    primary_mode: str,
    secondary_modes: list[str] | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    secondary = list(secondary_modes or [])
    records = query_public_knowledge_v2(question, state=state, limit=limit)
    source_entries = []
    for mode in list(dict.fromkeys([primary_mode, *secondary])):
        source_entries.extend(match_sources(question, state=state, module=mode, limit=4))

    jurisdiction = get_jurisdiction_context(state)
    official_sources = []
    if jurisdiction:
        official_sources = [
            {"title": source.title, "url": source.url, "source_type": source.source_type}
            for source in jurisdiction.sources
        ]

    curated_sources = [
        {
            "title": entry.title,
            "url": entry.source_url,
            "summary": entry.summary,
            "trust_level": entry.trust_level,
            "source_type": entry.entry_type,
            "state": entry.state,
        }
        for entry in source_entries
    ]
    urls = [record.get("source_url") for record in records]
    urls.extend(item["url"] for item in curated_sources)
    urls.extend(item["url"] for item in official_sources)
    clean_urls = list(dict.fromkeys(str(url) for url in urls if str(url or "").startswith("http")))

    if records:
        status = "curated_evidence_match"
    elif jurisdiction:
        status = "official_registry_only"
    else:
        status = "operational_guidance_only"

    return {
        "status": status,
        "verified_rule_available": bool(records),
        "warning": (
            "Official registry links identify where to verify the rule but do not prove an exact current requirement."
            if status == "official_registry_only"
            else ""
        ),
        "jurisdiction": jurisdiction.to_dict() if jurisdiction else None,
        "curated_records": [_record_view(record) for record in records],
        "curated_sources": curated_sources,
        "official_sources": official_sources,
        "source_urls": clean_urls,
    }
