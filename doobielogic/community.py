from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4


@dataclass
class VerificationReport:
    verified: bool
    trusted_sources: list[str]
    untrusted_sources: list[str]
    checked_at: str
    notes: str


@dataclass
class CommunityAnswer:
    answer_id: str
    responder_role: Literal["buyer", "operator", "compliance", "analyst", "other"]
    answer_text: str
    sources: list[str]
    verification: VerificationReport
    created_at: str


@dataclass
class CommunityQuestion:
    question_id: str
    asked_by: str
    role: Literal["buyer", "operator", "compliance", "analyst", "other"]
    state: str
    question_text: str
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    answers: list[CommunityAnswer] = field(default_factory=list)


class CommunityStore:
    def __init__(self):
        self._questions: dict[str, CommunityQuestion] = {}

    def create_question(self, asked_by: str, role: str, state: str, question_text: str, tags: list[str]) -> CommunityQuestion:
        q = CommunityQuestion(
            question_id=str(uuid4()),
            asked_by=asked_by,
            role=role,
            state=state.upper(),
            question_text=question_text,
            tags=tags,
        )
        self._questions[q.question_id] = q
        return q

    def list_questions(self, state: str | None = None, tag: str | None = None) -> list[CommunityQuestion]:
        items = list(self._questions.values())
        if state:
            items = [q for q in items if q.state == state.upper()]
        if tag:
            items = [q for q in items if tag in q.tags]
        return sorted(items, key=lambda q: q.created_at, reverse=True)

    def get_question(self, question_id: str) -> CommunityQuestion | None:
        return self._questions.get(question_id)

    def add_answer(self, question_id: str, answer: CommunityAnswer) -> CommunityQuestion | None:
        q = self._questions.get(question_id)
        if not q:
            return None
        q.answers.append(answer)
        return q


def new_answer_id() -> str:
    return str(uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
