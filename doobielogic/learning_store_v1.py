from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass
class LearningEvent:
    timestamp_utc: str
    mode: str
    question: str
    state: str | None
    outcome: str
    recommendation: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None


_EVENTS: list[LearningEvent] = []


def log_event(*, mode: str, question: str, state: str | None, outcome: str, recommendation: str | None = None, notes: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    event = LearningEvent(
        timestamp_utc=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        mode=mode,
        question=question,
        state=state.upper() if isinstance(state, str) else None,
        outcome=outcome,
        recommendation=recommendation,
        notes=notes,
        metadata=metadata or {},
    )
    _EVENTS.append(event)
    return asdict(event)


def summarize_learning(mode: str | None = None) -> dict[str, Any]:
    rows = [e for e in _EVENTS if mode is None or e.mode == mode]
    helpful = sum(1 for e in rows if e.outcome.lower() in {"helpful", "accepted", "used"})
    not_helpful = sum(1 for e in rows if e.outcome.lower() in {"not_helpful", "rejected", "ignored"})
    return {
        "event_count": len(rows),
        "helpful_count": helpful,
        "not_helpful_count": not_helpful,
        "recent": [asdict(e) for e in rows[-10:]],
        "confidence_bias": "up" if helpful > not_helpful else "down" if not_helpful > helpful else "flat",
    }
