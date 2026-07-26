from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ProfessionalDomain:
    mode: str
    label: str
    purpose: str
    core_topics: tuple[str, ...]
    key_metrics: tuple[str, ...]
    decision_rules: tuple[str, ...]
    required_evidence: tuple[str, ...]
    safety_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PROFESSIONAL_DOMAINS: dict[str, ProfessionalDomain] = {
    "quality": ProfessionalDomain(
        "quality",
        "Quality Assurance",
        "Protect product identity, consistency, release decisions, traceability, and corrective-action effectiveness.",
        ("deviations", "CAPA", "change control", "complaints", "holds", "recalls", "supplier quality"),
        ("right-first-time", "deviation recurrence", "CAPA age", "complaint rate", "hold age", "recall readiness"),
        (
            "Contain product and preserve evidence before diagnosing or correcting it.",
            "Separate symptom correction from verified root cause and effectiveness checks.",
            "Do not release held product without authorized quality disposition and required regulatory clearance.",
        ),
        ("lot and product identity", "batch and test records", "deviation timeline", "distribution record", "change history"),
        "Do not make a release, recall, remediation, or destruction decision without the approved quality system and jurisdiction rules.",
    ),
    "laboratory": ProfessionalDomain(
        "laboratory",
        "Laboratory & Testing",
        "Protect sample integrity, method control, defensible results, and timely investigation of anomalous testing.",
        ("sampling", "chain of custody", "method suitability", "calibration", "quality controls", "OOS investigation", "data integrity"),
        ("turnaround time", "invalid run rate", "OOS rate", "retest rate", "control failures", "sample rejection rate"),
        (
            "Quarantine affected product while sample, method, instrument, and batch causes are investigated.",
            "Never test into compliance through undocumented repeat testing.",
            "Preserve raw data, audit trails, chain of custody, and investigation approvals.",
        ),
        ("sample plan", "chain of custody", "raw data", "method version", "calibration and controls", "analyst and instrument"),
        "Only an authorized laboratory and quality process may invalidate, retest, report, or amend a regulated result.",
    ),
    "distribution": ProfessionalDomain(
        "distribution",
        "Distribution & Wholesale",
        "Move released cannabis products accurately, securely, and profitably through licensed handoffs.",
        ("order allocation", "manifests", "chain of custody", "delivery routing", "wholesale service", "returns", "receivables"),
        ("OTIF", "fill rate", "order cycle time", "delivery exceptions", "damage rate", "DSO", "return rate"),
        (
            "Ship only released product to verified authorized destinations using current required records.",
            "Reconcile every physical handoff to order, lot/package identity, quantity, and receiving evidence.",
            "Treat delivery exceptions and refused product as controlled inventory events.",
        ),
        ("customer and license", "order", "released lot/package", "manifest", "vehicle and driver", "proof of delivery"),
        "Transport, routing, vehicle, custody, return, and manifest requirements are jurisdiction-specific and must be verified before movement.",
    ),
    "security": ProfessionalDomain(
        "security",
        "Security & Data Protection",
        "Protect people, regulated inventory, cash, credentials, facilities, and audit evidence.",
        ("physical access", "video", "alarms", "cash control", "inventory diversion", "cybersecurity", "incident response"),
        ("access exceptions", "unexplained variances", "alarm response", "camera uptime", "privileged accounts", "incident closure time"),
        (
            "Protect people first, then contain access and preserve evidence.",
            "Use least privilege, individual accounts, dual control, and auditable approvals for sensitive actions.",
            "Do not overwrite logs or repeatedly correct inventory before the incident timeline is preserved.",
        ),
        ("user and access logs", "video and alarm events", "inventory audit trail", "cash records", "device and network events"),
        "Escalate immediate danger to emergency services and follow legal notification, evidence, privacy, and labor requirements.",
    ),
    "finance": ProfessionalDomain(
        "finance",
        "Finance & Commercial Performance",
        "Translate cannabis operating performance into cash, margin, working-capital, and investment decisions.",
        ("gross margin", "cash flow", "budgeting", "unit economics", "inventory valuation", "receivables", "capital allocation"),
        ("gross profit", "contribution margin", "cash conversion", "inventory turns", "DSO", "budget variance", "return on invested capital"),
        (
            "Bridge financial changes to operational drivers rather than explaining them with averages.",
            "Separate revenue, mix, price, discount, cost, waste, and timing effects.",
            "Protect cash and compliance before pursuing volume that destroys contribution.",
        ),
        ("period and entity", "general ledger", "sales and discounts", "COGS", "inventory", "labor", "receivables and payables"),
        "Do not provide tax, accounting, financing, valuation, or investment conclusions without qualified review and complete records.",
    ),
    "people": ProfessionalDomain(
        "people",
        "People & Workforce",
        "Build a trained, accountable, safely staffed cannabis workforce with clear roles and permissions.",
        ("workforce planning", "hiring", "credentialing", "onboarding", "training", "performance", "succession", "labor relations"),
        ("time to proficiency", "training completion", "turnover", "absence", "schedule adherence", "incident rate", "manager span"),
        (
            "Define the controlled tasks, evidence of competence, and permissions before assigning work.",
            "Train against approved SOPs and verify observed competence rather than attendance alone.",
            "Separate performance evidence from protected or legally restricted employment information.",
        ),
        ("role description", "license or badge requirements", "training matrix", "schedule", "performance record", "policy"),
        "Employment, background, scheduling, wage, accommodation, privacy, and discipline requirements need qualified local review.",
    ),
    "maintenance": ProfessionalDomain(
        "maintenance",
        "Engineering & Maintenance",
        "Protect safe capacity, environmental control, equipment reliability, calibration, and production continuity.",
        ("preventive maintenance", "critical spares", "calibration", "utilities", "downtime", "work orders", "change control"),
        ("uptime", "MTBF", "MTTR", "PM compliance", "repeat failure", "maintenance backlog", "spares availability"),
        (
            "Rank assets by safety, quality, compliance, and production consequence.",
            "Repair the failure mechanism and verify return to service before closing the work order.",
            "Route changes affecting validated processes, monitoring, or product contact through change control.",
        ),
        ("asset and criticality", "failure history", "work orders", "manual and limits", "calibration", "parts and downtime"),
        "Do not bypass guards, interlocks, lockout/tagout, manufacturer limits, or validated controls to restore output.",
    ),
    "marketing": ProfessionalDomain(
        "marketing",
        "Marketing & Customer Growth",
        "Grow compliant, measurable demand without unsupported claims or margin-destructive promotion.",
        ("audience", "positioning", "campaigns", "loyalty", "promotions", "attribution", "content approval"),
        ("incremental gross profit", "conversion", "repeat rate", "CAC", "redemption", "opt-out rate", "compliance rejection rate"),
        (
            "Define the business objective, eligible audience, offer economics, and measurement plan before launch.",
            "Measure incrementality and contribution, not clicks or redemptions alone.",
            "Approve claims, channels, audience restrictions, and required disclosures for the jurisdiction.",
        ),
        ("jurisdiction", "audience", "channel", "creative and claims", "offer cost", "baseline", "attribution window"),
        "Advertising, health claims, age gating, geofencing, loyalty, messaging, and promotion rules vary by jurisdiction.",
    ),
    "product_development": ProfessionalDomain(
        "product_development",
        "Product Development",
        "Move cannabis product ideas through consumer need, feasibility, safety, compliance, costing, scale-up, and launch control.",
        ("consumer need", "concept", "formulation", "prototype", "stability", "packaging", "costing", "scale-up"),
        ("stage-gate cycle time", "target cost", "first-pass quality", "stability success", "launch service level", "complaint rate"),
        (
            "Define target consumer, use occasion, format, dose architecture, price, cost, and jurisdiction before development.",
            "Lock critical quality attributes and test methods before scale-up.",
            "Do not launch until formula, process, label, packaging, testing, costing, and supply readiness are approved.",
        ),
        ("product brief", "formula and input specifications", "prototype results", "test and stability plan", "label", "costed BOM"),
        "Do not infer safe formulation, dose, shelf life, claims, or release status without validated development and qualified review.",
    ),
    "ehs": ProfessionalDomain(
        "ehs",
        "Environmental Health & Safety",
        "Prevent worker injury, hazardous exposure, fire, environmental loss, and unsafe operating shortcuts.",
        ("hazard assessment", "PPE", "SDS", "chemical safety", "ergonomics", "emergency response", "waste", "energy and water"),
        ("recordable incidents", "near misses", "training completion", "corrective-action age", "energy intensity", "water intensity", "waste rate"),
        (
            "Stop work and protect people when an uncontrolled hazard or exposure may exist.",
            "Use the hierarchy of controls before relying on PPE alone.",
            "Normalize environmental use to production and protect validated product and safety controls during conservation work.",
        ),
        ("task and hazard", "SDS and equipment", "exposure or incident facts", "training", "controls", "utility and production data"),
        "Emergency response, medical treatment, hazardous materials, worker reporting, and environmental obligations require qualified local authority.",
    ),
}


def get_professional_domain(mode: str) -> ProfessionalDomain | None:
    return PROFESSIONAL_DOMAINS.get(str(mode or "").strip().casefold())


def professional_domain_prompt(mode: str) -> str:
    domain = get_professional_domain(mode)
    if domain is None:
        return ""
    return "\n".join(
        (
            f"Professional domain: {domain.label}",
            f"Purpose: {domain.purpose}",
            "Core topics: " + ", ".join(domain.core_topics),
            "Key metrics: " + ", ".join(domain.key_metrics),
            "Decision rules:",
            *(f"- {rule}" for rule in domain.decision_rules),
            "Required evidence: " + ", ".join(domain.required_evidence),
            f"Safety boundary: {domain.safety_boundary}",
        )
    )


def professional_domain_result(question: str, mode: str) -> dict[str, Any] | None:
    domain = get_professional_domain(mode)
    if domain is None:
        return None
    return {
        "answer": (
            f"Start this {domain.label.lower()} review by defining the decision, preserving the relevant records, "
            f"and comparing the current result with an approved baseline. The first controls to apply are: "
            + " ".join(domain.decision_rules[:2])
        ),
        "explanation": (
            f"{domain.purpose} I need {', '.join(domain.required_evidence)} to move from a general playbook "
            "to a facility-specific conclusion."
        ),
        "recommendations": [
            domain.decision_rules[0],
            domain.decision_rules[1],
            f"Provide: {', '.join(domain.required_evidence)}.",
        ],
        "confidence": "low",
        "sources": [f"[professional_domain:{domain.mode}]"],
        "mode": domain.mode,
        "routed_mode": domain.mode,
        "route_label": domain.label,
        "risk_flags": [domain.safety_boundary],
        "inefficiencies": [],
        "question": question,
    }


def professional_domain_catalog() -> dict[str, dict[str, Any]]:
    return {mode: domain.to_dict() for mode, domain in PROFESSIONAL_DOMAINS.items()}
