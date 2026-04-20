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
from doobielogic.response_system import RESPONSE_BUILDERS, infer_confidence
from doobielogic.sourcepack import build_grounded_summary

Persona = Literal[
    "buyer",
    "inventory",
    "extraction",
    "ops",
    "copilot",
    "compliance",
    "executive",
    "retail_ops",
    "cultivation",
    "kitchen",
    "packaging",
]

PERSONA_GUIDANCE: dict[str, str] = {
    "buyer": "Prioritize assortment gaps, margin, turns, velocity, promos, and practical reorder logic.",
    "inventory": "Prioritize low stock, overstock, days-on-hand imbalance, and tactical replenishment actions.",
    "extraction": "Prioritize yield variance, stage loss, failed batches, and throughput stabilization.",
    "ops": "Prioritize SOP reliability, KPI stability, bottleneck removal, and staffing execution.",
    "copilot": "Give a direct answer first, then the shortest practical action.",
    "compliance": "Prioritize regulator-backed guidance, repeat issue control, and corrective action closure.",
    "executive": "Prioritize concise cross-functional bottlenecks, recurring risk, and decision-ready actions.",
    "retail_ops": "Prioritize staffing, throughput, SOP execution, conversion, and store-level process control.",
    "cultivation": "Prioritize room performance, quality risk, cycle stability, and yield reliability.",
    "kitchen": "Prioritize dosage control, QC stability, sanitation discipline, and handoff reliability.",
    "packaging": "Prioritize label accuracy, reconciliation, completion rate, and line stability.",
}

MODULE_MAP = {
    "buyer": "retail",
    "inventory": "retail",
    "extraction": "operations",
    "ops": "operations",
    "copilot": "operations",
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
    risk_flags: list[str]
    inefficiencies: list[str]
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

    def _intel_mode(self, mode: str) -> str:
        if mode in {"buyer", "inventory", "extraction", "compliance", "executive", "financial"}:
            return mode
        if mode in {"retail_ops", "cultivation", "kitchen", "packaging", "ops", "copilot"}:
            return mode
        return "executive"

    def _builder_mode(self, mode: str) -> str:
        if mode in RESPONSE_BUILDERS:
            return mode
        return "copilot"

    def _compose_response(
        self,
        mode: str,
        quick_answer: str,
        explanation_context: str,
        recommendations: list[str],
        confidence: str,
        sources: list[str],
        risk_flags: list[str] | None = None,
        inefficiencies: list[str] | None = None,
        analysis: CannabisOutput | None = None,
    ) -> CopilotResponse:
        builder_mode = self._builder_mode(mode)
        structured = RESPONSE_BUILDERS[builder_mode](
            quick_answer=quick_answer,
            explanation_context=explanation_context,
            recommendations=recommendations,
            risk_flags=risk_flags or [],
            inefficiencies=inefficiencies or [],
            confidence=confidence,
            sources=sources,
        )
        return CopilotResponse(**structured.to_dict(), analysis=analysis)

    def _extract_inefficiencies(self, mode: str, data: dict[str, Any], insights: dict[str, Any] | None = None) -> list[str]:
        inefficiencies: list[str] = []
        insights = insights or {}
        if mode in {"buyer", "inventory"}:
            low_velocity = int(insights.get("low_velocity_count", 0) or 0)
            zero_qty = int(insights.get("zero_quantity_count", 0) or 0)
            high_inv = int(insights.get("high_inventory_count", 0) or 0)
            if low_velocity > 0:
                inefficiencies.append(f"{low_velocity} low-velocity rows are slowing turns.")
            if zero_qty > 0:
                inefficiencies.append(f"{zero_qty} SKUs show zero sell-through in this snapshot.")
            if high_inv > 0:
                inefficiencies.append(f"{high_inv} rows are carrying above-average on-hand inventory.")
        if mode == "extraction":
            yield_pct = self._to_float(data.get("yield_pct") or data.get("yield"))
            failed_batches = self._to_float(data.get("failed_batches"))
            margin_per_g = self._to_float(data.get("margin_per_gram"))
            if yield_pct is not None and yield_pct < 0.6:
                inefficiencies.append("Yield is below target, reducing extraction value per run.")
            if failed_batches is not None and failed_batches > 0:
                inefficiencies.append("Failed batches are constraining throughput and margin capture.")
            if margin_per_g is not None and margin_per_g < 0:
                inefficiencies.append("Negative margin per gram indicates run economics are underwater.")
        if mode == "retail_ops":
            if self._to_float(data.get("conversion_rate")) is not None and float(data.get("conversion_rate")) < 0.18:
                inefficiencies.append("Conversion is below target and likely tied to floor execution or availability gaps.")
            if self._to_float(data.get("queue_wait_minutes")) is not None and float(data.get("queue_wait_minutes")) > 8:
                inefficiencies.append("Queue wait time is above service-level target and reduces throughput.")
        if mode == "cultivation":
            if sum(1 for x in data.get("microbial_risk_flag", []) if bool(x)) > 0:
                inefficiencies.append("Microbial flags indicate cultivation control drift and release delays.")
        if mode == "kitchen":
            if sum(1 for x in data.get("rework_flag", []) if bool(x)) > 0:
                inefficiencies.append("Kitchen rework is consuming capacity and delaying release.")
        if mode == "packaging":
            if sum(1 for x in data.get("label_error_flag", []) if bool(x)) > 0:
                inefficiencies.append("Packaging label errors are driving rework and compliance exposure.")
        return inefficiencies

    def _detect_mode_risks(self, mode: str, context: dict[str, Any], data: dict[str, Any], insights: dict[str, Any] | None = None) -> list[str]:
        risks: list[str] = list(context.get("risk_flags", []) or [])
        insights = insights or {}

        if mode in {"buyer", "inventory"}:
            if int(insights.get("high_inventory_count", 0) or 0) > 0:
                risks.append("high DOH / overstock pressure detected in uploaded inventory rows")
            if int(insights.get("low_velocity_count", 0) or 0) > 0:
                risks.append("low sell-through concentration risk in current assortment")
            if int(insights.get("zero_quantity_count", 0) or 0) > 0:
                risks.append("low-stock pressure likely on active velocity SKUs")

        if mode == "extraction":
            yield_pct = self._to_float(data.get("yield_pct") or data.get("yield"))
            failed_batches = self._to_float(data.get("failed_batches"))
            margin_per_g = self._to_float(data.get("margin_per_gram"))
            if yield_pct is not None and yield_pct < 0.6:
                risks.append("low yield")
            if failed_batches is not None and failed_batches > 0:
                risks.append("failed batches")
            if margin_per_g is not None and margin_per_g < 0:
                risks.append("negative margin")
            if data.get("unmapped_output_type"):
                risks.append("unmapped output type")
        if mode == "retail_ops":
            if self._to_float(data.get("conversion_rate")) is not None and float(data.get("conversion_rate")) < 0.18:
                risks.append("low conversion rate")
            if self._to_float(data.get("discount_rate")) is not None and float(data.get("discount_rate")) > 0.18:
                risks.append("discount overuse risk")
        if mode == "cultivation":
            if sum(1 for x in data.get("microbial_risk_flag", []) if bool(x)) > 0:
                risks.append("microbial flags")
            if sum(1 for x in data.get("moisture_risk_flag", []) if bool(x)) > 0:
                risks.append("moisture instability")
        if mode == "kitchen":
            if sum(1 for x in data.get("sanitation_gap_flag", []) if bool(x)) > 0:
                risks.append("sanitation gap")
            if self._to_float(data.get("dosage_variance_pct")) is not None and float(data.get("dosage_variance_pct")) > 10:
                risks.append("dosage variance")
        if mode == "packaging":
            if sum(1 for x in data.get("label_error_flag", []) if bool(x)) > 0:
                risks.append("label error risk")
            if any(abs(float(x)) > 2 for x in data.get("reconciliation_variance", []) if x is not None):
                risks.append("reconciliation variance")

        deduped: list[str] = []
        for risk in risks:
            safe = str(risk).strip()
            if safe and safe not in deduped:
                deduped.append(safe)
        return deduped

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def ask(self, question: str, persona: Persona = "buyer", state: str | None = None) -> CopilotResponse:
        safe_persona = self._normalize_persona(persona)
        safe_state = state.upper() if isinstance(state, str) and state.strip() else None
        grounded = build_grounded_summary(question=question, state=safe_state, module=MODULE_MAP[safe_persona])
        knowledge = search_department_knowledge(safe_persona if safe_persona != "ops" else "executive", question, limit=5)
        context_mode = "ops" if safe_persona in {"ops", "executive"} else safe_persona
        context = build_doobie_context(data={}, mode=self._intel_mode(context_mode), question=question)

        confidence = infer_confidence(
            has_structured_data=False,
            has_grounding=bool(grounded.get("answer")),
            has_relevant_rules=bool(knowledge),
            weak_context=True,
        )
        explanation = "\n\n".join(
            [
                f"Role lens: {PERSONA_GUIDANCE[safe_persona]}",
                render_department_knowledge_summary(knowledge),
                "Grounded source context:\n" + grounded["answer"],
            ]
        )
        answer = f"{safe_persona.title()} brief ready with {confidence} confidence."

        risks = self._detect_mode_risks(context_mode, context, data={})
        inefficiencies = self._extract_inefficiencies(context_mode, data={})
        return self._compose_response(
            mode=context_mode,
            quick_answer=answer,
            explanation_context=explanation,
            recommendations=self._recommendations_for(safe_persona),
            confidence=confidence,
            sources=grounded.get("sources", []),
            risk_flags=risks,
            inefficiencies=inefficiencies,
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
        dept = (department or "").lower()
        outputs = build_operations_outputs(parsed_data=parsed_data, department=dept, state=safe_state)
        grounded = build_grounded_summary(question=question, state=safe_state, module=MODULE_MAP.get(safe_persona, "operations"))
        dept_mode_map = {
            "retail_ops": "retail_ops",
            "buyer": "retail_ops",
            "cultivation": "cultivation",
            "extraction": "extraction",
            "kitchen": "kitchen",
            "packaging": "packaging",
            "compliance": "compliance",
        }
        context_mode = dept_mode_map.get(dept, safe_persona if safe_persona in dept_mode_map.values() else "executive")
        context = build_doobie_context(data=parsed_data or {}, mode=self._intel_mode(context_mode), question=question)

        has_data = bool(parsed_data)
        has_rules = bool(outputs.get("knowledge_hits")) or bool(outputs.get("recommendations"))
        has_unmapped = bool((parsed_data or {}).get("unmapped_output_type"))
        confidence = infer_confidence(
            has_structured_data=has_data,
            has_grounding=bool(grounded.get("answer")),
            has_relevant_rules=has_rules,
            has_unmapped_outputs=has_unmapped,
            weak_context=not has_data,
        )

        explanation = "\n\n".join(
            [
                f"Role lens: {PERSONA_GUIDANCE.get(safe_persona, PERSONA_GUIDANCE['executive'])}",
                outputs["knowledge_summary"],
                render_operations_summary(outputs, department=dept),
                "Grounded source context:\n" + grounded["answer"],
            ]
        )
        answer = f"{dept.title()} operations brief generated with {confidence} confidence."
        risks = self._detect_mode_risks(context_mode, context, data=parsed_data or {})
        inefficiencies = self._extract_inefficiencies(context_mode, data=parsed_data or {})

        return self._compose_response(
            mode=context_mode,
            quick_answer=answer,
            explanation_context=explanation,
            recommendations=self._recommendations_for(safe_persona),
            confidence=confidence,
            sources=grounded.get("sources", []),
            risk_flags=risks,
            inefficiencies=inefficiencies,
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
        context_mode = "inventory" if safe_persona == "buyer" else (safe_persona if safe_persona in {"retail_ops", "cultivation", "kitchen", "packaging", "compliance", "executive", "extraction"} else "ops")
        context = build_doobie_context(data=mapped_data or {}, mode=self._intel_mode(context_mode), question=question)

        answer_sections = [
            f"Role lens: {PERSONA_GUIDANCE[safe_persona]}",
            "File intelligence:\n" + data_summary,
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

        has_data = bool(mapped_data)
        has_rules = bool(recommendations)
        confidence = infer_confidence(
            has_structured_data=has_data,
            has_grounding=bool(grounded.get("answer")),
            has_relevant_rules=has_rules,
            weak_context=not has_data,
        )
        answer = f"{safe_persona.title()} analysis prepared with structured context and source grounding ({confidence} confidence)."

        risks = self._detect_mode_risks(context_mode, context, data=mapped_data or {}, insights=data_insights)
        inefficiencies = self._extract_inefficiencies(context_mode, data=mapped_data or {}, insights=data_insights)
        return self._compose_response(
            mode=context_mode,
            quick_answer=answer,
            explanation_context=explanation,
            recommendations=recommendations,
            confidence=confidence,
            sources=grounded.get("sources", []),
            risk_flags=risks,
            inefficiencies=inefficiencies,
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
        has_rules = bool(analysis.recommendations) and bool(analysis.regulation_links)
        confidence = infer_confidence(
            has_structured_data=True,
            has_grounding=bool(grounded.get("answer")),
            has_relevant_rules=has_rules,
        )
        answer = f"Score {analysis.score} ({analysis.tier}) with {analysis.compliance_risk} compliance risk ({confidence} confidence)."
        sources = list(dict.fromkeys((analysis.regulation_links or {}).values())) + grounded.get("sources", [])

        context_mode = "inventory" if safe_persona == "buyer" else safe_persona
        context = build_doobie_context(data=payload.model_dump(), mode=self._intel_mode(context_mode), question="inventory risk promotions compliance assortment pricing days on hand")
        risks = self._detect_mode_risks(context_mode, context, data=payload.model_dump())
        inefficiencies = self._extract_inefficiencies(context_mode, data=payload.model_dump())
        return self._compose_response(
            mode=context_mode,
            quick_answer=answer,
            explanation_context=explanation,
            recommendations=analysis.recommendations,
            confidence=confidence,
            sources=sources,
            risk_flags=risks,
            inefficiencies=inefficiencies,
            analysis=analysis,
        )

    def _recommendations_for(self, persona: str) -> list[str]:
        bank = {
            "buyer": [
                "Close assortment gaps in top-velocity categories before adding long-tail SKUs.",
                "Cut dead inventory with margin-protected markdown ladders and transfer options.",
            ],
            "inventory": [
                "Rebalance low-stock and high-DOH SKUs with immediate transfer/reorder actions.",
                "Set DOH guardrails by category and escalate outliers weekly.",
            ],
            "extraction": [
                "Benchmark yield and terpene retention by input lot, stage, and operator.",
                "Escalate failed-batch root causes with SOP checkpoints and release controls.",
            ],
            "ops": [
                "Map bottlenecks by department and assign owners for weekly closure.",
                "Standardize SOP checklists across shifts and track adherence.",
            ],
            "copilot": [
                "Start with the highest-impact operational fix that can be executed this week.",
            ],
            "compliance": [
                "Review repeat issue concentration and CAPA aging weekly.",
                "Verify traceability records before release/transfer decisions.",
            ],
            "executive": [
                "Prioritize recurring cross-functional risk themes over one-off noise.",
                "Use concise risk-impact-action cadence for decision reviews.",
            ],
            "retail_ops": [
                "Schedule labor to peak demand windows and pre-stage backup coverage for queue spikes.",
                "Protect conversion by prioritizing shelf/menu availability for top-velocity SKUs.",
                "Use attach coaching and discount discipline to improve ATV without margin erosion.",
            ],
            "cultivation": [
                "Track canopy productivity by room/cultivar and triage persistent underperformers.",
                "Stabilize harvest cadence and dry-room controls before expanding plant count.",
                "Segment biomass early for premium, extraction, and trim pathways.",
            ],
            "kitchen": [
                "Tighten infusion homogeneity checks and in-process potency verification.",
                "Reduce hold/rework by enforcing sanitation and allergen changeover controls.",
                "Synchronize cooling and packaging handoff slots to avoid batch aging delays.",
            ],
            "packaging": [
                "Run shift-start label preflight and quarantine any mismatched templates immediately.",
                "Balance lines around bottleneck stations and track first-pass yield by SKU.",
                "Escalate reconciliation variance and require supervisor signoff on corrective counts.",
            ],
        }
        return bank.get(persona, bank["buyer"])
