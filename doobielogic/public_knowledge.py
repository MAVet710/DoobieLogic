from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any


@dataclass(frozen=True)
class PublicKnowledgeRecord:
    record_id: str
    state: str | None
    domain: str
    topic: str
    title: str
    summary: str
    source_url: str
    source_type: str
    trust_level: str
    keywords: tuple[str, ...]
    update_cadence: str | None = None
    notes: str | None = None


@lru_cache(maxsize=1)
def load_public_knowledge() -> tuple[PublicKnowledgeRecord, ...]:
    with resources.files("data").joinpath("public_knowledge_seed.json").open("r", encoding="utf-8") as f:
        raw: list[dict[str, Any]] = json.load(f)
    return tuple(
        PublicKnowledgeRecord(
            record_id=str(item["record_id"]),
            state=item.get("state"),
            domain=str(item["domain"]),
            topic=str(item["topic"]),
            title=str(item["title"]),
            summary=str(item["summary"]),
            source_url=str(item["source_url"]),
            source_type=str(item["source_type"]),
            trust_level=str(item["trust_level"]),
            keywords=tuple(item.get("keywords", [])),
            update_cadence=item.get("update_cadence"),
            notes=item.get("notes"),
        )
        for item in raw
    )


def query_public_knowledge(
    question: str,
    *,
    state: str | None = None,
    domain: str | None = None,
    limit: int = 8,
) -> list[PublicKnowledgeRecord]:
    q = (question or "").lower()
    target_state = state.upper() if isinstance(state, str) and state.strip() else None
    scored: list[tuple[int, PublicKnowledgeRecord]] = []

    for entry in load_public_knowledge():
        if target_state and entry.state not in {None, target_state}:
            continue
        if domain and entry.domain != domain:
            continue

        score = 0
        if target_state and entry.state == target_state:
            score += 5
        if entry.domain in q:
            score += 2
        if entry.topic.lower() in q:
            score += 2
        for kw in entry.keywords:
            if kw.lower() in q:
                score += 2
        if score > 0:
            scored.append((score, entry))

    scored.sort(
        key=lambda item: (item[0], 1 if item[1].trust_level == "high" else 0),
        reverse=True,
    )
    return [entry for _, entry in scored[:limit]]


def build_public_knowledge_summary(
    question: str,
    *,
    state: str | None = None,
    domain: str | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    matches = query_public_knowledge(question, state=state, domain=domain, limit=limit)
    if not matches:
        return {
            "answer": "No public-knowledge seed matches were found for that query yet.",
            "sources": [],
            "confidence": "low",
            "grounding": "Public knowledge seed",
            "matches": [],
        }

    lines = [
        f"- {m.title}: {m.summary}"
        for m in matches[: min(4, len(matches))]
    ]
    return {
        "answer": "\n".join(lines),
        "sources": [m.source_url for m in matches],
        "confidence": "high" if any(m.trust_level == "high" for m in matches) else "medium",
        "grounding": "Public knowledge seed",
        "matches": [m.__dict__ for m in matches],
    }


def buyer_context_payload(*, state: str | None = None) -> dict[str, Any]:
    records = [r for r in load_public_knowledge() if r.domain in {"buyer", "market", "compliance", "tracking"}]
    if state:
        records = [r for r in records if r.state in {None, state.upper()}]
    return {
        "record_count": len(records),
        "states": sorted({r.state for r in records if r.state}),
        "domains": sorted({r.domain for r in records}),
        "records": [r.__dict__ for r in records],
    }
