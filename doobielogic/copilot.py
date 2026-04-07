from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from doobielogic.engine import CannabisLogicEngine
from doobielogic.models import CannabisInput, CannabisOutput
from doobielogic.parser import analyze_mapped_data, render_insight_summary
from doobielogic.buyer_brain import render_buyer_brain_summary, summarize_buyer_opportunities
from doobielogic.sourcepack import build_grounded_summary

Persona = Literal["buyer", "retail_ops", "compliance", "extraction", "executive"]

PERSONA_GUIDANCE: dict[Persona, str] = {
    "buyer": "Prioritize assortment gaps, margin, turns, velocity, promos, and practical reorder logic.",
    "retail_ops": "Prioritize staffing, throughput, SOP execution, customer experience, conversion, and store-level process control.",
    "compliance": "Prioritize regulator-backed guidance, labeling, packaging, manifests, tracking, and documented risk areas.",
    "extraction": "Prioritize yield, batch control, release checks, throughput, solvent safety, and lot traceability.",
    "executive": "Prioritize cross-functional risk, revenue health, cash efficiency, and concise decisions with operational tradeoffs.",
}

MODULE_MAP: dict[Persona, str] = {
    "buyer": "retail",
    "retail_ops": "operations",
    "compliance": "compliance",
    "extraction": "operations",
    "executive": "operations",
}


@dataclass
class CopilotResponse:
    answer: str
    grounding: str
    confidence: str
    sources: list[str]
    suggestions: list[str]
    analysis: CannabisOutput | None = None


class DoobieCopilot:
    def __init__(self, engine: CannabisLogicEngine | None = None):
        self.engine = engine or CannabisLogicEngine()

    def ask(self, question: str, persona: Persona = "buyer", state: str | None = None) -> CopilotResponse:
        safe_persona = persona if persona in PERSONA_GUIDANCE else "buyer"
        safe_state = state.upper() if isinstance(state, str) and state.strip() else None
        grounded = build_grounded_summary(question=question, state=safe_state, module=MODULE_MAP[safe_persona])
        guidance = PERSONA_GUIDANCE[safe_persona]
        answer_parts = [
            f"Role lens: {guidance}",
            grounded["answer"],
        ]
        suggestions = self._suggestions_for(safe_persona)
        return CopilotResponse(
            answer="\n\n".join(answer_parts),
            grounding=grounded["grounding"],
            confidence=grounded["confidence"],
            sources=grounded.get("sources", []),
            suggestions=suggestions,
        )


    def ask_with_buyer_brain(
        self,
        question: str,
        mapped_data: dict[str, list | tuple | object] | None,
        persona: Persona = "buyer",
        state: str | None = None,
    ) -> CopilotResponse:
        safe_persona = persona if persona in PERSONA_GUIDANCE else "buyer"
        safe_state = state.upper() if isinstance(state, str) and state.strip() else None
        grounded = build_grounded_summary(question=question, state=safe_state, module=MODULE_MAP[safe_persona])

        data_insights = analyze_mapped_data(mapped_data or {}) if mapped_data else {}
        data_summary = render_insight_summary(data_insights)

        answer_sections = [
            f"Role lens: {PERSONA_GUIDANCE[safe_persona]}",
            "File intelligence:\n" + data_summary,
        ]

        if safe_persona == "buyer" and mapped_data:
            buyer_results = summarize_buyer_opportunities(mapped_data)
            answer_sections.append(render_buyer_brain_summary(buyer_results))
        elif mapped_data:
            answer_sections.append("Buyer-specific recommendations are limited for this role unless directly supported by uploaded file fields.")

        answer_sections.append("Grounded source context:\n" + grounded["answer"])

        return CopilotResponse(
            answer="\n\n".join(answer_sections),
            grounding=grounded["grounding"],
            confidence=grounded["confidence"],
            sources=grounded.get("sources", []),
            suggestions=self._suggestions_for(safe_persona),
        )

    def analyze_and_explain(self, payload: CannabisInput, persona: Persona = "buyer") -> CopilotResponse:
        analysis = self.engine.analyze(payload)
        state = payload.state
        question = "inventory risk promotions compliance assortment pricing days on hand"
        grounded = build_grounded_summary(question=question, state=state, module=MODULE_MAP[persona])
        answer = (
            f"Role lens: {PERSONA_GUIDANCE[persona]}\n\n"
            f"Score: {analysis.score} ({analysis.tier})\n"
            f"Compliance risk: {analysis.compliance_risk}\n"
            f"Inventory stress: {analysis.inventory_stress}\n"
            f"Market pressure: {analysis.market_pressure}\n\n"
            f"Recommendations:\n- " + "\n- ".join(analysis.recommendations)
        )
        return CopilotResponse(
            answer=answer,
            grounding=grounded["grounding"],
            confidence=grounded["confidence"],
            sources=list(dict.fromkeys((analysis.regulation_links or {}).values())) + grounded.get("sources", []),
            suggestions=self._suggestions_for(persona),
            analysis=analysis,
        )

    def _suggestions_for(self, persona: Persona) -> list[str]:
        bank = {
            "buyer": [
                "Ask me to find assortment gaps by category or price band.",
                "Ask me to turn KPI signals into a vendor strategy or reorder plan.",
            ],
            "retail_ops": [
                "Ask me to translate weak KPIs into store-level action steps.",
                "Ask me to draft an EOD recap or operator update.",
            ],
            "compliance": [
                "Ask me to ground a compliance topic in trusted sources.",
                "Ask me to flag where a response is heuristic versus source-backed.",
            ],
            "extraction": [
                "Ask me to frame extraction issues around throughput, release checks, and traceability.",
                "Ask me to turn process pain points into an SOP checklist.",
            ],
            "executive": [
                "Ask me for an executive summary of performance and risk.",
                "Ask me to condense operational findings into decision-ready bullets.",
            ],
        }
        return bank[persona]
