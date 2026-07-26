from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class IntelligenceRoute:
    mode: str
    label: str
    reason: str


_MODE_LABELS = {
    "buyer": "Buying & Inventory",
    "retail_ops": "Retail Operations",
    "cultivation": "Cultivation",
    "extraction": "Extraction",
    "kitchen": "Kitchen & Manufacturing",
    "packaging": "Packaging",
    "ops": "Operations",
    "compliance": "Compliance",
    "executive": "Executive",
    "quality": "Quality Assurance",
    "laboratory": "Laboratory & Testing",
    "distribution": "Distribution & Wholesale",
    "security": "Security & Loss Prevention",
    "finance": "Finance & Unit Economics",
    "people": "People & Training",
    "maintenance": "Maintenance & Reliability",
    "marketing": "Marketing & Customer Growth",
    "product_development": "Product Development",
    "ehs": "Environmental Health & Safety",
    "copilot": "Cannabis Copilot",
}

_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "compliance",
        (
            "compliance",
            "compliant",
            "regulation",
            "regulatory",
            "metrc",
            "traceability",
            "law",
            "legal",
            "license",
            "testing requirement",
            "state rule",
            "adult use",
            "adult-use",
            "medical cannabis limit",
            "purchase limit",
            "daily limit",
            "transaction limit",
            "possession limit",
            "dispensing limit",
            "consumer limit",
            "patient limit",
            "how much cannabis",
            "how much marijuana",
            "transfer cannabis",
            "transfer marijuana",
            "records must",
            "record retention",
            "retain for",
            "id verification",
        ),
    ),
    (
        "laboratory",
        (
            "laboratory",
            "lab result",
            "lab testing",
            "chain of custody",
            "out of specification",
            "oos",
            "retest",
            "sampling plan",
            "certificate of analysis",
            "coa",
            "analytical method",
        ),
    ),
    (
        "quality",
        (
            "quality assurance",
            "quality system",
            "qa review",
            "capa",
            "corrective action",
            "deviation",
            "change control",
            "product complaint",
            "recall",
            "quarantine",
            "release decision",
        ),
    ),
    (
        "security",
        (
            "security",
            "camera",
            "alarm",
            "theft",
            "diversion",
            "cash shortage",
            "cash variance",
            "data breach",
            "cybersecurity",
            "ransomware",
            "access control",
            "employee account",
        ),
    ),
    (
        "distribution",
        (
            "distribution",
            "wholesale",
            "shipment",
            "delivery route",
            "proof of delivery",
            "pod",
            "manifest",
            "otif",
            "fill rate",
            "receiving refusal",
        ),
    ),
    (
        "finance",
        (
            "cash flow",
            "cash forecast",
            "accounts receivable",
            "accounts payable",
            "budget variance",
            "contribution margin",
            "unit economics",
            "working capital",
            "collections",
        ),
    ),
    (
        "maintenance",
        (
            "preventive maintenance",
            "preventative maintenance",
            "equipment downtime",
            "equipment failure",
            "work order",
            "critical spares",
            "calibration",
            "mtbf",
            "mttr",
        ),
    ),
    (
        "product_development",
        (
            "new product",
            "product development",
            "research and development",
            "r&d",
            "prototype",
            "scale-up",
            "stability study",
            "launch gate",
        ),
    ),
    (
        "marketing",
        (
            "marketing",
            "advertising",
            "campaign",
            "customer acquisition cost",
            "cac",
            "loyalty",
            "email campaign",
            "sms campaign",
            "promotion performance",
        ),
    ),
    (
        "people",
        (
            "hiring",
            "onboarding",
            "employee training",
            "training matrix",
            "turnover",
            "performance review",
            "succession",
            "workforce plan",
            "new hire",
        ),
    ),
    (
        "ehs",
        (
            "worker safety",
            "workplace safety",
            "injury",
            "near miss",
            "ppe",
            "safety data sheet",
            "sds",
            "hazard assessment",
            "chemical exposure",
            "ergonomic",
            "energy use",
            "water use",
            "environmental",
            "sustainability",
        ),
    ),
    (
        "extraction",
        (
            "extraction",
            "extract",
            "extraction yield",
            "oil yield",
            "process yield",
            "recovery",
            "solvent",
            "distillate",
            "rosin",
            "resin",
            "biomass",
            "failed batch",
            "hydrocarbon",
            "run yield",
            "residual solvent",
        ),
    ),
    (
        "cultivation",
        (
            "cultivation",
            "cultivate",
            "harvest",
            "flower room",
            "veg room",
            "plant",
            "canopy",
            "crop",
            "grow",
        ),
    ),
    (
        "kitchen",
        (
            "kitchen",
            "edible",
            "infusion",
            "recipe",
            "batch potency",
            "cook",
            "gummy",
            "beverage",
            "plan production",
            "required ship date",
        ),
    ),
    (
        "packaging",
        (
            "packaging",
            "package",
            "label",
            "labeling",
            "packout",
            "child resistant",
            "finished goods",
            "mislabel",
            "mislabeling",
            "label error",
        ),
    ),
    (
        "buyer",
        (
            "inventory",
            "buyer",
            "buying",
            "purchase order",
            "open to buy",
            "open-to-buy",
            "otb",
            "reorder",
            "sell through",
            "sell-through",
            "slow mover",
            "markdown",
            "stockout",
            "assortment",
            "sku",
            "vendor",
            "minimum order",
            "moq",
            "negative on-hand",
            "negative on hand",
        ),
    ),
    (
        "retail_ops",
        (
            "retail",
            "dispensary",
            "budtender",
            "store",
            "basket",
            "conversion",
            "promotion",
            "merchandising",
            "attach rate",
            "wait time",
        ),
    ),
    (
        "executive",
        (
            "executive",
            "board",
            "company-wide",
            "company wide",
            "leadership",
            "strategic",
            "profitability",
            "margin",
            "forecast",
            "weekly operating review",
            "operating review agenda",
        ),
    ),
    (
        "ops",
        (
            "operations",
            "workflow",
            "bottleneck",
            "throughput",
            "capacity",
            "labor",
            "schedule",
            "process",
            "inefficiency",
        ),
    ),
)

_COLUMN_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("extraction", ("input_weight", "output_weight", "extraction_yield", "solvent", "failed_batches")),
    ("cultivation", ("harvest", "strain", "plant", "canopy", "flower_room")),
    ("kitchen", ("recipe", "servings", "potency", "ingredient", "infusion")),
    ("packaging", ("package", "label", "packout", "units_packaged")),
    ("buyer", ("sku", "inventory", "sales", "on_hand", "cost", "price", "category")),
)

_ROLE_DEFAULTS = {
    "buyer": "buyer",
    "operations": "ops",
    "compliance": "compliance",
    "analyst": "copilot",
    "viewer": "copilot",
    "admin": "copilot",
}


def _column_names(data: Mapping[str, Any] | None) -> set[str]:
    if not data:
        return set()
    return {str(key).strip().casefold() for key in data}


def _contains_keyword(text: str, keyword: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text) is not None


def infer_intelligence_route(
    question: str,
    *,
    data: Mapping[str, Any] | None = None,
    user_role: str | None = None,
) -> IntelligenceRoute:
    """Choose a cannabis intelligence workflow without exposing a mode selector."""

    text = str(question or "").strip().casefold()
    for mode, keywords in _KEYWORDS:
        if any(_contains_keyword(text, keyword) for keyword in keywords):
            return IntelligenceRoute(mode, _MODE_LABELS[mode], "Detected from your question")

    columns = _column_names(data)
    for mode, hints in _COLUMN_HINTS:
        if any(any(hint in column for hint in hints) for column in columns):
            return IntelligenceRoute(mode, _MODE_LABELS[mode], "Detected from the uploaded data")

    role_mode = _ROLE_DEFAULTS.get(str(user_role or "").strip().casefold(), "copilot")
    return IntelligenceRoute(role_mode, _MODE_LABELS[role_mode], "Selected automatically for this conversation")


def available_mode_labels() -> Sequence[str]:
    return tuple(_MODE_LABELS.values())
