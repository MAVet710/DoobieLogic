from __future__ import annotations

from dataclasses import dataclass

from doobielogic.knowledge import CannabisKnowledgeBase


PERSONA_PROMPTS = {
    "buyer": "Focus on assortment, margin, turns, promo strategy, and compliant purchasing decisions.",
    "sales": "Focus on account planning, pipeline quality, sell-through, reorder cadence, and retailer enablement.",
    "cultivation": "Focus on canopy health, IPM, harvest planning, and post-harvest quality controls.",
    "extraction": "Focus on throughput, yield, solvent safety, QA release, and SOP consistency.",
    "operations": "Focus on SOPs, staffing, compliance checkpoints, and process KPIs.",
}


@dataclass
class ChatResponse:
    answer: str
    citations: list[str]
    suggested_actions: list[str]


class CannabisOpsAssistant:
    def __init__(self, knowledge_base: CannabisKnowledgeBase | None = None):
        self.knowledge_base = knowledge_base or CannabisKnowledgeBase()

    def chat(self, question: str, persona: str = "buyer", limit: int = 5) -> ChatResponse:
        result = self.knowledge_base.ask(question, limit=limit)
        persona_text = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS["operations"])

        action_bank = {
            "buyer": [
                "Review 30-day sell-through by SKU tier and remove low-turn tail inventory.",
                "Align promo depth with margin floor and state promotional rules.",
            ],
            "sales": [
                "Prioritize accounts with strongest reorder velocity and category fit.",
                "Build account plans around retailer KPI gaps and compliance-safe promos.",
            ],
            "cultivation": [
                "Audit environmental setpoints and IPM records for top-value rooms.",
                "Track harvest timing against potency and terpene retention targets.",
            ],
            "extraction": [
                "Validate solvent residual testing and batch release checklist compliance.",
                "Benchmark yield and terpene retention by input material lot.",
            ],
            "operations": [
                "Map process bottlenecks and define weekly KPI review cadence.",
                "Standardize SOP checklists across departments and shifts.",
            ],
        }

        citations = list({m["source_url"] for m in result.get("matches", [])[:limit]})
        answer = (
            f"Role guidance: {persona_text}\n\n"
            f"Cannabis answer:\n{result['answer']}"
        )

        return ChatResponse(
            answer=answer,
            citations=citations,
            suggested_actions=action_bank.get(persona, action_bank["operations"]),
        )
