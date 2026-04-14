from __future__ import annotations

from typing import Any

from doobielogic.public_knowledge_records_v2 import PUBLIC_KNOWLEDGE_RECORDS_V2


def query_public_knowledge_v2(question: str, state: str | None = None, domain: str | None = None, limit: int = 8) -> list[dict[str, Any]]:
    q = (question or "").lower()
    state = state.upper() if isinstance(state, str) else None
    scored: list[tuple[int, dict[str, Any]]] = []

    for rec in PUBLIC_KNOWLEDGE_RECORDS_V2:
        if state and rec.get("state") not in {None, state}:
            continue
        if domain and rec.get("domain") != domain:
            continue

        score = 0
        if state and rec.get("state") == state:
            score += 5
        if rec.get("topic", "").lower() in q:
            score += 2
        if rec.get("domain", "").lower() in q:
            score += 1
        for kw in rec.get("keywords", []):
            if str(kw).lower() in q:
                score += 2

        if score > 0:
            scored.append((score, rec))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:limit]]


def build_public_context_v2(question: str, state: str | None = None, domain: str | None = None) -> dict[str, Any]:
    matches = query_public_knowledge_v2(question, state=state, domain=domain)
    return {
        "match_count": len(matches),
        "sources": [m["source_url"] for m in matches],
        "context": matches,
        "grounding": "Regulator + peer-reviewed sources",
        "confidence": "high" if matches else "low",
    }
