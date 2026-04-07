from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from doobielogic.department_knowledge import render_department_knowledge_summary, search_department_knowledge
from doobielogic.operations_engine import build_operations_outputs, render_operations_summary
from doobielogic.engine import CannabisLogicEngine
from doobielogic.models import CannabisInput, CannabisOutput
from doobielogic.parser import analyze_mapped_data, render_insight_summary
from doobielogic.buyer_brain import render_buyer_brain_summary, summarize_buyer_opportunities
from doobielogic.sourcepack import build_grounded_summary

Persona = Literal["buyer", "retail_ops", "cultivation", "extraction", "kitchen", "packaging", "compliance", "executive"]

PERSONA_GUIDANCE: dict[Persona, str] = {
    "buyer": "Prioritize assortment gaps, margin, turns, velocity, promos, and practical reorder logic.",
    "retail_ops": "Prioritize staffing, throughput, SOP execution, conversion, and store-level process control.",
    "cultivation": "Prioritize room performance, quality risk, cycle stability, and yield reliability.",
    "extraction": "Prioritize batch consistency, throughput, downtime, and release readiness.",
    "kitchen": "Prioritize dosage control, QC stability, sanitation discipline, and handoff reliability.",
    "packaging": "Prioritize label accuracy, reconciliation, completion rate, and line stability.",
    "compliance": "Prioritize regulator-backed guidance, repeat issue control, and corrective action closure.",
    "executive": "Prioritize concise cross-functional bottlenecks, recurring risk, and decision-ready actions.",
}

MODULE_MAP = {
    "buyer": "retail",
    "retail_ops": "operations",
    "cultivation": "operations",
    "extraction": "operations",
    "kitchen": "operations",
    "packaging": "operations",
    "compliance": "compliance",
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
        knowledge = search_department_knowledge(safe_persona if safe_persona != "buyer" else "retail_ops", question, limit=3)
        answer_parts = [
            f"Role lens: {PERSONA_GUIDANCE[safe_persona]}",
            render_department_knowledge_summary(knowledge),
            "Grounded source context:\n" + grounded["answer"],
        ]
        return CopilotResponse(
            answer="\n\n".join(answer_parts),
            grounding=grounded["grounding"],
            confidence=grounded["confidence"],
            sources=grounded.get("sources", []),
            suggestions=self._suggestions_for(safe_persona),
        )

    def ask_with_operations(self, question: str, department: str, parsed_data: dict | None, persona: Persona = "executive", state: str | None = None) -> CopilotResponse:
        safe_persona = persona if persona in PERSONA_GUIDANCE else "executive"
        safe_state = state.upper() if isinstance(state, str) and state.strip() else None
        outputs = build_operations_outputs(parsed_data=parsed_data, department=department, state=safe_state)
        grounded = build_grounded_summary(question=question, state=safe_state, module=MODULE_MAP.get(safe_persona, "operations"))
        answer = "\n\n".join(
            [
                f"Role lens: {PERSONA_GUIDANCE[safe_persona]}",
                outputs["knowledge_summary"],
                render_operations_summary(outputs, department=department),
                "Grounded source context:\n" + grounded["answer"],
            ]
        )
        return CopilotResponse(
            answer=answer,
            grounding=grounded["grounding"],
            confidence=grounded["confidence"],
            sources=grounded.get("sources", []),
            suggestions=self._suggestions_for(safe_persona),
        )

    def ask_with_buyer_brain(self, question: str, mapped_data: dict[str, list] | None, persona: Persona = "buyer", state: str | None = None) -> CopilotResponse:
        safe_persona = persona if persona in PERSONA_GUIDANCE else "buyer"
        safe_state = state.upper() if isinstance(state, str) and state.strip() else None
        grounded = build_grounded_summary(question=question, state=safe_state, module=MODULE_MAP[safe_persona])

        data_insights = analyze_mapped_data(mapped_data or {}) if mapped_data else {}
        data_summary = render_insight_summary(data_insights)
        answer_sections = [f"Role lens: {PERSONA_GUIDANCE[safe_persona]}", "File intelligence:\n" + data_summary]
        if safe_persona in {"buyer", "retail_ops"} and mapped_data:
            buyer_results = summarize_buyer_opportunities(mapped_data)
            answer_sections.append(render_buyer_brain_summary(buyer_results))
        elif mapped_data:
            answer_sections.append("Department-specific operational analysis is preferred for this persona; buyer-only claims are minimized.")
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
        grounded = build_grounded_summary(question="inventory risk promotions compliance assortment pricing days on hand", state=payload.state, module="operations")
        answer = (
            f"Role lens: {PERSONA_GUIDANCE.get(persona, PERSONA_GUIDANCE['buyer'])}\n\n"
            f"Score: {analysis.score} ({analysis.tier})\n"
            f"Compliance risk: {analysis.compliance_risk}\n"
            f"Inventory stress: {analysis.inventory_stress}\n"
            f"Market pressure: {analysis.market_pressure}\n\n"
            f"Recommendations:\n- " + "\n- ".join(analysis.recommendations)
        )
        return CopilotResponse(answer=answer, grounding=grounded["grounding"], confidence=grounded["confidence"], sources=list(dict.fromkeys((analysis.regulation_links or {}).values())) + grounded.get("sources", []), suggestions=self._suggestions_for(persona if persona in PERSONA_GUIDANCE else "buyer"), analysis=analysis)

    def _suggestions_for(self, persona: Persona) -> list[str]:
        bank = {
            "buyer": ["Ask for slow movers, markdown flags, and reorder opportunities.", "Ask for price ladder and assortment concentration review."],
            "retail_ops": ["Ask for category friction and store execution priorities.", "Ask for concise store-level action checklist."],
            "cultivation": ["Ask for room underperformance and quality-risk drivers.", "Ask for cultivation action plan by room and cultivar."],
            "extraction": ["Ask for yield consistency and downtime pressure signals.", "Ask for extraction action plan by operator and output type."],
            "kitchen": ["Ask for dosage/QC risk and sanitation-related blockers.", "Ask for kitchen action plan by product type."],
            "packaging": ["Ask for label/reconciliation risk concentration.", "Ask for packaging action plan by line and shift."],
            "compliance": ["Ask for repeat issue concentration and CAPA aging.", "Ask for state-aware compliance action framing (not legal advice)."],
            "executive": ["Ask for concise cross-functional bottleneck summary.", "Ask for top recurring risks and owners."],
        }
        return bank[persona]
