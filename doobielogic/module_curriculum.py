from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ModuleCurriculum:
    mode: str
    purpose: str
    core_topics: tuple[str, ...]
    key_metrics: tuple[str, ...]
    decision_rules: tuple[str, ...]
    required_evidence: tuple[str, ...]
    safe_failure: str

    def to_dict(self) -> dict:
        return asdict(self)


MODULE_CURRICULA: dict[str, ModuleCurriculum] = {
    "buyer": ModuleCurriculum(
        mode="buyer",
        purpose="Improve assortment, availability, cash efficiency, and margin across regulated cannabis retail.",
        core_topics=("open-to-buy", "assortment architecture", "vendor performance", "pricing", "promotions", "SKU lifecycle"),
        key_metrics=("days on hand", "sell-through", "GMROI", "gross margin", "stockout rate", "inventory turns", "fill rate"),
        decision_rules=(
            "Protect proven velocity and known assortment gaps before adding long-tail SKUs.",
            "Balance margin with turns and carrying cost rather than maximizing margin percentage alone.",
            "Use staged markdowns and transfers before aging inventory becomes destruction risk.",
        ),
        required_evidence=("sales history", "on-hand inventory", "open purchase orders", "cost and price", "vendor fill history"),
        safe_failure="Ask for category, SKU, location, sales window, and inventory data before recommending an order quantity.",
    ),
    "inventory": ModuleCurriculum(
        mode="inventory",
        purpose="Protect availability, working capital, freshness, and compliant inventory disposition.",
        core_topics=("replenishment", "days on hand", "aging", "transfers", "markdowns", "stockouts", "reconciliation"),
        key_metrics=("days on hand", "weeks of supply", "sell-through", "inventory turns", "stockout rate", "shrink", "aging exposure"),
        decision_rules=(
            "Prioritize proven demand and near-term stockout exposure before speculative replenishment.",
            "Use transfers, purchase-order changes, and staged markdowns before inventory becomes obsolete.",
            "Escalate unexplained physical-to-system variance before making availability decisions.",
        ),
        required_evidence=("on-hand and available quantity", "sales history", "receipts", "open purchase orders", "transfers", "adjustments"),
        safe_failure="Do not recommend quantities or disposition without location, time window, demand, and on-hand evidence.",
    ),
    "retail_ops": ModuleCurriculum(
        mode="retail_ops",
        purpose="Improve compliant dispensary execution, customer flow, availability, and labor productivity.",
        core_topics=("conversion", "basket building", "menu accuracy", "queue flow", "labor scheduling", "discount discipline"),
        key_metrics=("conversion rate", "average transaction value", "units per transaction", "wait time", "sales per labor hour", "stockout rate"),
        decision_rules=(
            "Protect menu and shelf availability for top-velocity products.",
            "Schedule labor to demand windows and diagnose queue constraints before adding blanket labor.",
            "Evaluate promotions on incremental traffic, units, and margin—not redemption alone.",
        ),
        required_evidence=("transaction data", "traffic or queue data", "labor schedule", "menu availability", "discount detail"),
        safe_failure="Separate observed facts from general retail heuristics when store-level data is missing.",
    ),
    "cultivation": ModuleCurriculum(
        mode="cultivation",
        purpose="Stabilize compliant crop output, quality, cycle time, and room-level economics.",
        core_topics=("canopy planning", "environmental control", "irrigation", "IPM", "harvest cadence", "drying and curing", "testing"),
        key_metrics=("yield per canopy area", "grams per watt", "cycle days", "test pass rate", "waste rate", "labor hours", "room variance"),
        decision_rules=(
            "Compare cultivars within room and cycle cohorts before changing genetics.",
            "Treat microbial, moisture, and testing failures as release risks requiring root-cause review.",
            "Stabilize room execution and post-harvest controls before expanding plant count.",
        ),
        required_evidence=("room and cultivar", "environmental logs", "input schedule", "harvest weight", "test results", "waste events"),
        safe_failure="Do not prescribe pesticide, nutrient, or remediation actions without jurisdiction and product-label verification.",
    ),
    "extraction": ModuleCurriculum(
        mode="extraction",
        purpose="Improve safe, compliant extraction yield, quality, throughput, and run economics.",
        core_topics=("input quality", "mass balance", "yield", "solvent control", "decarboxylation", "fractionation", "rework", "batch release"),
        key_metrics=("yield percent", "recovery", "throughput", "downtime", "rework rate", "test pass rate", "cost per gram", "margin per gram"),
        decision_rules=(
            "Benchmark comparable methods, input lots, output types, equipment, and operators.",
            "Use mass balance and stage-loss analysis before changing process settings.",
            "Escalate residual solvent, contamination, failed-batch, and release-hold signals before optimizing yield.",
        ),
        required_evidence=("method", "input and output mass", "stage losses", "run settings", "test results", "downtime", "labor and material cost"),
        safe_failure="Never recommend unsafe pressure, temperature, solvent, or equipment settings without validated SOP and manufacturer limits.",
    ),
    "kitchen": ModuleCurriculum(
        mode="kitchen",
        purpose="Improve edible and infused-product potency consistency, food safety, yield, and release cadence.",
        core_topics=("formulation", "infusion", "homogeneity", "dosage control", "allergens", "sanitation", "batch records", "cooling"),
        key_metrics=("potency variance", "batch yield", "first-pass quality", "rework rate", "waste", "cycle time", "hold time"),
        decision_rules=(
            "Protect homogeneity, dosage, allergen, sanitation, and traceability controls before throughput.",
            "Compare expected and actual potency with validated sampling and testing methods.",
            "Investigate formulation, mixing, depositing, cooling, and packaging handoffs when variance recurs.",
        ),
        required_evidence=("master formula", "batch record", "ingredient lots", "in-process checks", "lab results", "sanitation and allergen records"),
        safe_failure="Do not invent formulations, dose claims, shelf life, or release decisions without validated records and applicable rules.",
    ),
    "packaging": ModuleCurriculum(
        mode="packaging",
        purpose="Improve compliant labeling, reconciliation, line throughput, and finished-goods release.",
        core_topics=("label control", "child resistance", "lot traceability", "line clearance", "reconciliation", "packout", "quality release"),
        key_metrics=("first-pass yield", "label error rate", "completion rate", "reconciliation variance", "scrap", "rework", "units per labor hour"),
        decision_rules=(
            "Quarantine label or traceability mismatches before continuing production.",
            "Use line-clearance and approved-artwork controls at every SKU or lot changeover.",
            "Escalate unexplained reconciliation variance and preserve an auditable correction trail.",
        ),
        required_evidence=("approved label", "product and lot identity", "packaging counts", "scrap and rework", "line clearance", "jurisdiction"),
        safe_failure="Do not approve a label from general guidance; cite the current jurisdiction rule and require qualified review.",
    ),
    "compliance": ModuleCurriculum(
        mode="compliance",
        purpose="Provide conservative, jurisdiction-specific operational compliance guidance grounded in official sources.",
        core_topics=("licensing", "track and trace", "testing", "packaging and labeling", "advertising", "transport", "security", "waste", "recalls"),
        key_metrics=("open findings", "repeat findings", "CAPA age", "training completion", "inventory variance", "test failures", "release holds"),
        decision_rules=(
            "Require a state or territory before giving jurisdiction-specific guidance.",
            "Cite the regulator or official rule source and expose review freshness in every answer.",
            "Fail safely when the exact current rule text is not in the curated corpus.",
        ),
        required_evidence=("jurisdiction", "program scope", "license type", "official source URL", "source review date", "specific operating facts"),
        safe_failure="State what is unknown, provide the official authority link, and require regulator or qualified-counsel verification.",
    ),
    "ops": ModuleCurriculum(
        mode="ops",
        purpose="Coordinate cross-functional cannabis operations, ownership, risk, and continuous improvement.",
        core_topics=("SOP execution", "capacity", "scheduling", "quality", "handoffs", "root cause", "CAPA", "accountability"),
        key_metrics=("throughput", "cycle time", "schedule attainment", "first-pass yield", "downtime", "rework", "on-time release"),
        decision_rules=(
            "Trace downstream symptoms to the earliest controllable process step.",
            "Assign an owner, due date, evidence standard, and follow-up cadence to corrective actions.",
            "Optimize the constraint while protecting safety, quality, and compliance gates.",
        ),
        required_evidence=("process map", "timestamps", "status and ownership", "quality events", "capacity and demand"),
        safe_failure="Keep recommendations at the diagnostic level when process evidence is incomplete.",
    ),
    "executive": ModuleCurriculum(
        mode="executive",
        purpose="Turn cross-functional cannabis operating evidence into prioritized, accountable decisions.",
        core_topics=("strategy", "working capital", "margin", "risk", "capacity", "quality", "compliance posture", "growth"),
        key_metrics=("revenue", "gross margin", "cash conversion", "inventory turns", "capacity utilization", "quality cost", "compliance exposure"),
        decision_rules=(
            "Prioritize recurring cross-functional constraints over one-off noise.",
            "Connect each recommendation to financial impact, operational risk, owner, and time horizon.",
            "Do not trade short-term volume for unmanaged legal, safety, or product-quality exposure.",
        ),
        required_evidence=("financial period", "operating KPIs", "risk register", "capacity", "inventory", "quality and compliance signals"),
        safe_failure="Label assumptions and request the missing executive evidence before quantifying impact.",
    ),
    "copilot": ModuleCurriculum(
        mode="copilot",
        purpose="Triage general cannabis-business questions and route them to the right specialist curriculum.",
        core_topics=("cannabis business", "operations", "retail", "production", "compliance"),
        key_metrics=("question-specific evidence coverage", "source freshness", "confidence"),
        decision_rules=("Route before answering.", "Prefer specialist curricula and source-backed evidence.", "Expose uncertainty."),
        required_evidence=("question", "jurisdiction when legally material", "relevant business context"),
        safe_failure="Ask for the minimum missing context or provide a conservative high-level answer.",
    ),
}


def get_module_curriculum(mode: str) -> ModuleCurriculum:
    return MODULE_CURRICULA.get(str(mode or "").strip().casefold(), MODULE_CURRICULA["copilot"])


def curriculum_prompt(mode: str) -> str:
    curriculum = get_module_curriculum(mode)
    return "\n".join(
        (
            f"Specialist module: {curriculum.mode}",
            f"Purpose: {curriculum.purpose}",
            "Core topics: " + ", ".join(curriculum.core_topics),
            "Key metrics: " + ", ".join(curriculum.key_metrics),
            "Decision rules:",
            *(f"- {rule}" for rule in curriculum.decision_rules),
            "Required evidence: " + ", ".join(curriculum.required_evidence),
            f"Safe failure: {curriculum.safe_failure}",
        )
    )


def curriculum_brief(mode: str) -> str:
    curriculum = get_module_curriculum(mode)
    return (
        f"Module curriculum: {curriculum.purpose} "
        f"Evidence required: {', '.join(curriculum.required_evidence)}. "
        f"Safe failure: {curriculum.safe_failure}"
    )
