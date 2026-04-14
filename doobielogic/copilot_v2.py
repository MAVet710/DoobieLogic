from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from doobielogic.intelligence_v2 import build_unified_intelligence


@dataclass
class CopilotV2Response:
    answer: str
    confidence: str
    sources: list[str]
    recommendations: list[str]
    raw: dict[str, Any]


class DoobieCopilotV2:
    def ask(
        self,
        question: str,
        *,
        mapped_data: dict[str, Any] | None = None,
        persona: str = "buyer",
        state: str | None = None,
    ) -> CopilotV2Response:
        result = build_unified_intelligence(
            question=question,
            mapped_data=mapped_data,
            persona=persona,
            state=state,
        )

        return CopilotV2Response(
            answer=result.get("answer", ""),
            confidence=result.get("confidence", "low"),
            sources=result.get("sources", []),
            recommendations=result.get("recommendations", []),
            raw=result,
        )
