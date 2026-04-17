from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from doobielogic.buyer_brain import render_buyer_brain_summary, summarize_buyer_opportunities
from doobielogic.cannabis_intelligence import build_doobie_context
from doobielogic.department_knowledge import render_department_knowledge_summary, search_department_knowledge
from doobielogic.engine import CannabisLogicEngine
from doobielogic.models import CannabisInput, CannabisOutput
from doobielogic.operations_engine import build_operations_outputs, render_operations_summary
from doobielogic.parser import analyze_mapped_data, render_insight_summary
from doobielogic.sourcepack import build_grounded_summary

Persona = Literal["buyer", "extraction", "ops", "compliance", "executive", "retail_ops", "cultivation", "kitchen", "packaging"]

PERSONA_GUIDANCE: dict[str, str] = {
    "buyer": "Prioritize assortment gaps, margin, turns, velocity, promos, and practical reorder logic.",
    "extraction": "Prioritize batch consistency, throughput, downtime, and release readiness.",
    "ops": "Prioritize SOP reliability, KPI stability, bottleneck removal, and staffing execution.",
    "compliance": "Prioritize regulator-backed guidance, repeat issue control, and corrective action closure.",
    "executive": "Prioritize concise cross-functional bottlenecks, recurring risk, and decision-ready actions.",
    "retail_ops": "Prioritize staffing, throughput, SOP execution, conversion, and store-level process control.",
    "cultivation": "Prioritize room performance, quality risk, cycle stability, and yield reliability.",
    "kitchen": "Prioritize dosage control, QC stability, sanitation discipline, and handoff reliability.",
    "packaging": "Prioritize label accuracy, reconciliation, completion rate, and line stability.",
}

MODULE_MAP = {
    "buyer": "retail",
    "extraction": "operations",
    "ops": "operations",
    "compliance": "compliance",
    "executive": "operations",
    "retail_ops": "operations",
    "cultivation": "operations",
    "kitchen": "operations",
    "packaging": "operations",
}


@dataclass
class CopilotResponse:
    answer: str
    explanation: str
    recommendations: list[str]
    confidence: str
    sources: list[str]
    mode: str
    analysis: CannabisOutput | None = None


class DoobieCopilot:
    def __init__(self, engine: CannabisLogicEngine | None = None):
        self.engine = engine or CannabisLogicEngine()

    def _normalize_persona(self, persona: str | None) -> str:
        safe = (persona or "buyer").strip().lower()
        if safe in {"inventory", "buyer_brief"}:
            return "buyer"
        if safe in {"operations", "ops"}:
            return "ops"
        return safe if safe in PERSONA_GUIDANCE else "buyer"

    def _response(
        self,
        answer: str,
        explanation: str,
        recommendations: list[str],
        confidence: str,
        sources: list[str],
        mode: str,
        analysis: CannabisOutput | None = None,
    ) -> CopilotResponse:
        return CopilotResponse(
            answer=answer,
            explanation=explanation,
            recommendations=recommendations,
            confidence=confidence,
            sources=sources,
            mode=mode,
            analysis=analysis,
        )

    def ask(self, question: str, persona: Persona = "buyer", state: str | None = None) -> CopilotResponse:
        safe_persona = self._normalize_persona(persona)
        safe_state = state.upper() if isinstance(state, str) and state.strip() else None
        grounded = build_grounded_summary(question=question, state=safe_state, module=MODULE_MAP[safe_persona])
        knowledge = search_department_knowledge(safe_persona if safe_persona != "ops" else "executive", question, limit=5)
        context = build_doobie_context(data={}, mode="ops" if safe_persona in {"ops", "executive"} else safe_persona, question=question, state=safe_state)

        explanation = "\n\n".join(
            [
                f"Role lens: {PERSONA_GUIDANCE[safe_persona]}",
                render_department_knowledge_summary(knowledge),
                f"Context risks: {', '.join(context['risk_flags']) if context['risk_flags'] else 'No immediate risk flags from provided data.'}",
                "Grounded source context:\n" + grounded["answer"],
            ]
        )
        answer = f"{safe_persona.title()} brief ready. {grounded['confidence']} confidence based on available context."
        return self._response(
            answer=answer,
            explanation=explanation,
            recommendations=self._recommendations_for(safe_persona),
            confidence=grounded["confidence"],
            sources=grounded.get("sources", []),
            mode=safe_persona,
        )

    def ask_with_operations(
        self,
        question: str,
        department: str,
        parsed_data: dict | None,
        persona: Persona = "executive",
        state: str | None = None,
    ) -> CopilotResponse:
        safe_persona = self._normalize_persona(persona)
        safe_state = state.upper() if isinstance(state, str) and state.strip() else None
        outputs = build_operations_outputs(parsed_data=parsed_data, department=department, state=safe_state)
        grounded = build_grounded_summary(question=question, state=safe_state, module=MODULE_MAP.get(safe_persona, "operations"))
        context_mode = "extraction" if department == "extraction" else "ops"
        context = build_doobie_context(data=parsed_data or {}, mode=context_mode, question=question, state=safe_state)
        explanation = "\n\n".join(
            [
                f"Role lens: {PERSONA_GUIDANCE.get(safe_persona, PERSONA_GUIDANCE['executive'])}",
                outputs["knowledge_summary"],
                render_operations_summary(outputs, department=department),
                f"Structured risk flags: {', '.join(context['risk_flags']) if context['risk_flags'] else 'none'}",
                "Grounded source context:\n" + grounded["answer"],
            ]
        )
        answer = f"{department.title()} operations brief generated with {grounded['confidence']} confidence."
        return self._response(
            answer=answer,
            explanation=explanation,
            recommendations=self._recommendations_for(safe_persona),
            confidence=grounded["confidence"],
            sources=grounded.get("sources", []),
            mode=context_mode,
        )

    def ask_with_buyer_brain(
        self,
        question: str,
        mapped_data: dict[str, Any] | None,
        persona: Persona = "buyer",
        state: str | None = None,
    ) -> CopilotResponse:
        safe_persona = self._normalize_persona(persona)
        safe_state = state.upper() if isinstance(state, str) and state.strip() else None
        grounded = build_grounded_summary(question=question, state=safe_state, module=MODULE_MAP[safe_persona])

        data_insights = analyze_mapped_data(mapped_data or {}) if mapped_data else {}
        data_summary = render_insight_summary(data_insights)
        context_mode = "inventory" if safe_persona == "buyer" else "ops"
        context = build_doobie_context(data=mapped_data or {}, mode=context_mode, question=question, state=safe_state)

        answer_sections = [
            f"Role lens: {PERSONA_GUIDANCE[safe_persona]}",
            "File intelligence:\n" + data_summary,
            f"Structured risk flags: {', '.join(context['risk_flags']) if context['risk_flags'] else 'none'}",
        ]

        recommendations = self._recommendations_for(safe_persona)
        if safe_persona == "buyer" and mapped_data:
            buyer_results = summarize_buyer_opportunities(mapped_data)
            answer_sections.append(render_buyer_brain_summary(buyer_results))
            recommendations = buyer_results.get("markdown_candidates", {}).get("candidates", [])[:5] or recommendations
        elif mapped_data:
            answer_sections.append("Buyer-specific recommendations are limited for this role unless directly supported by uploaded file fields.")

        answer_sections.append("Grounded source context:\n" + grounded["answer"])
        explanation = "\n\n".join(answer_sections)
        answer = f"{safe_persona.title()} analysis prepared with structured context and source grounding."

        return self._response(
            answer=answer,
            explanation=explanation,
            recommendations=recommendations,
            confidence=grounded["confidence"],
            sources=grounded.get("sources", []),
            mode=context_mode,
        )

    def analyze_and_explain(self, payload: CannabisInput, persona: Persona = "buyer") -> CopilotResponse:
        safe_persona = self._normalize_persona(persona)
        analysis = self.engine.analyze(payload)
        grounded = build_grounded_summary(
            question="inventory risk promotions compliance assortment pricing days on hand",
            state=payload.state,
            module="operations",
        )
        explanation = (
            f"Role lens: {PERSONA_GUIDANCE.get(safe_persona, PERSONA_GUIDANCE['buyer'])}\n\n"
            f"Score: {analysis.score} ({analysis.tier})\n"
            f"Compliance risk: {analysis.compliance_risk}\n"
            f"Inventory stress: {analysis.inventory_stress}\n"
            f"Market pressure: {analysis.market_pressure}\n\n"
            f"Recommendations:\n- " + "\n- ".join(analysis.recommendations)
        )
        answer = f"Score {analysis.score} ({analysis.tier}) with {analysis.compliance_risk} compliance risk."
        sources = list(dict.fromkeys((analysis.regulation_links or {}).values())) + grounded.get("sources", [])
        return self._response(
            answer=answer,
            explanation=explanation,
            recommendations=analysis.recommendations,
            confidence=grounded["confidence"],
            sources=sources,
            mode=safe_persona,
            analysis=analysis,
        )

    def _recommendations_for(self, persona: str) -> list[str]:
        bank = {
            "buyer": [
                "Review 30-day sell-through by SKU tier and reduce low-turn tail inventory.",
                "Align promo depth with margin floor and avoid destructive discounting.",
            ],
            "extraction": [
                "Benchmark yield and terpene retention by input lot and operator.",
                "Escalate failed-batch root causes with SOP and QA checkpoints.",
            ],
            "ops": [
                "Map bottlenecks by department and assign owners for weekly closure.",
                "Standardize SOP checklists across shifts and track adherence.",
            ],
            "compliance": [
                "Review repeat issue concentration and CAPA aging weekly.",
                "Verify traceability records before release/transfer decisions.",
            ],
            "executive": [
                "Prioritize recurring cross-functional risk themes over one-off noise.",
                "Use concise risk-impact-action cadence for decision reviews.",
            ],
            "retail_ops": ["Tighten staffing to demand windows.", "Simplify category mix and price ladders."],
            "cultivation": ["Audit room-level yield variance.", "Escalate repeated microbial flags."],
            "kitchen": ["Audit dosage drift by batch.", "Reduce sanitation-related hold events."],
            "packaging": ["Escalate repeat labeling failures.", "Track reconciliation variance by shift."],
        }
        return bank.get(persona, bank["buyer"])
