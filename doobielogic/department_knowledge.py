from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DepartmentKnowledgeEntry:
    department: str
    topic: str
    title: str
    summary: str
    guidance: str
    source_type: str
    trust_level: str
    keywords: tuple[str, ...]


_ENTRIES: tuple[DepartmentKnowledgeEntry, ...] = (
    # Cultivation
    DepartmentKnowledgeEntry("cultivation", "yield variance", "Room-level yield variance matters", "Wide room-to-room yield spread can hide process drift.", "Review cultivar/room trends before changing genetics.", "grounded_operational_reference", "high", ("room", "yield", "variance", "cultivar")),
    DepartmentKnowledgeEntry("cultivation", "cycle efficiency", "Cycle-time creep signals hidden inefficiency", "Longer flowering or dry-back cycles can reduce annual turns.", "Track cycle_days by room and phase weekly.", "heuristic_operational_pattern", "medium", ("cycle", "days", "efficiency", "phase")),
    DepartmentKnowledgeEntry("cultivation", "quality risk", "Repeated microbial flags raise post-harvest risk", "Repeated microbial hits increase release delays and rework.", "Escalate sanitation and environmental controls for flagged rooms.", "grounded_operational_reference", "high", ("microbial", "risk", "qc", "test")),
    DepartmentKnowledgeEntry("cultivation", "moisture control", "Moisture flags often precede quality failures", "Moisture issues can compound mold and cure instability.", "Tighten dry room SOP and moisture checkpoints.", "grounded_operational_reference", "high", ("moisture", "dry", "flag")),
    DepartmentKnowledgeEntry("cultivation", "waste", "High waste concentration deserves root-cause review", "Waste spikes can indicate process, labor, or genetics problems.", "Segment waste by room and phase before corrective action.", "heuristic_operational_pattern", "medium", ("waste", "trim", "loss")),
    DepartmentKnowledgeEntry("cultivation", "testing", "Unstable pass rates reduce planning confidence", "Low pass-rate consistency creates unpredictable sellable output.", "Pair pass-rate trends with moisture and microbial events.", "grounded_operational_reference", "high", ("test pass", "pass rate", "stability")),
    DepartmentKnowledgeEntry("cultivation", "supply planning", "Uneven room output destabilizes supply", "Inconsistent harvest cadence causes downstream planning friction.", "Balance canopy plans across rooms and harvest windows.", "heuristic_operational_pattern", "medium", ("supply", "planning", "harvest")),
    DepartmentKnowledgeEntry("cultivation", "canopy density", "Canopy density should align with output quality", "High plant_count without stable output can increase risk.", "Benchmark canopy_sqft and plant_count by top rooms.", "heuristic_operational_pattern", "medium", ("canopy", "plant count", "density")),
    DepartmentKnowledgeEntry("cultivation", "underperformance", "Cultivar underperformance should be explicit", "Some cultivars repeatedly underperform in specific rooms.", "Use cultivar-room scorecards before expansion.", "heuristic_operational_pattern", "medium", ("strain", "cultivar", "underperform")),
    DepartmentKnowledgeEntry("cultivation", "execution", "Standard work reduces volatility", "Room SOP consistency usually narrows output dispersion.", "Audit SOP adherence when volatility expands.", "grounded_operational_reference", "high", ("sop", "execution", "consistency")),
    # Extraction
    DepartmentKnowledgeEntry("extraction", "yield consistency", "Consistency beats one-off peak batches", "Stable yield across lots is operationally healthier than isolated spikes.", "Track yield dispersion, not just max yield.", "grounded_operational_reference", "high", ("yield", "consistency", "batch")),
    DepartmentKnowledgeEntry("extraction", "downtime", "Downtime can outweigh headline yield", "High downtime shrinks true throughput even if yield looks strong.", "Monitor downtime by line and operator.", "heuristic_operational_pattern", "medium", ("downtime", "throughput")),
    DepartmentKnowledgeEntry("extraction", "rework", "Rework concentration is an escalation signal", "Rework-heavy lots increase labor and release risk.", "Escalate lots/operators with repeat rework.", "grounded_operational_reference", "high", ("rework", "batch status")),
    DepartmentKnowledgeEntry("extraction", "quality", "Failed/flagged batches need urgency", "Fail/flag clusters indicate process drift or control gaps.", "Prioritize CAPA on residual solvent and pass/fail trends.", "grounded_operational_reference", "high", ("pass fail", "residual", "flag")),
    DepartmentKnowledgeEntry("extraction", "mix", "Output-type mix can distort efficiency", "Comparing yield across output types without segmentation is misleading.", "Benchmark by output_type cohorts.", "heuristic_operational_pattern", "medium", ("output type", "mix", "efficiency")),
    DepartmentKnowledgeEntry("extraction", "operator variance", "Operator variance points to SOP gaps", "Large operator spread may indicate training inconsistency.", "Pair variance review with standardized setup checks.", "heuristic_operational_pattern", "medium", ("operator", "variance", "training")),
    DepartmentKnowledgeEntry("extraction", "turnaround", "Turnaround time controls responsiveness", "Slow turnaround reduces release cadence and planning reliability.", "Track turnaround_hours by status and output type.", "grounded_operational_reference", "high", ("turnaround", "hours")),
    DepartmentKnowledgeEntry("extraction", "solvent", "Residual solvent flags are high-priority", "Residual solvent events are quality and compliance-sensitive.", "Escalate solvent control checks for flagged lots.", "grounded_regulatory_theme", "high", ("residual solvent", "compliance")),
    DepartmentKnowledgeEntry("extraction", "status aging", "Aging in flagged status increases risk", "Batches stuck in non-release status consume capacity.", "Create queue limits for flagged or hold states.", "heuristic_operational_pattern", "medium", ("status", "hold", "queue")),
    DepartmentKnowledgeEntry("extraction", "throughput", "Throughput requires both yield and uptime", "Good yield with poor uptime often misses demand windows.", "Use combined yield-uptime scorecards.", "heuristic_operational_pattern", "medium", ("uptime", "throughput", "yield")),
    # Kitchen
    DepartmentKnowledgeEntry("kitchen", "dosage control", "Dosage drift is a priority risk", "Dosage variance can trigger quality failures and rework.", "Track expected vs actual dosage by batch.", "grounded_operational_reference", "high", ("dosage", "variance", "qc")),
    DepartmentKnowledgeEntry("kitchen", "qc stability", "QC pass-rate instability needs escalation", "Volatile qc_pass_rate lowers confidence in release timing.", "Review QC by shift and product_type.", "grounded_operational_reference", "high", ("qc", "pass rate")),
    DepartmentKnowledgeEntry("kitchen", "sanitation", "Sanitation gaps can cascade into delays", "Sanitation misses often create hold/rework chains.", "Audit sanitation_gap_flag on repeat lines.", "grounded_operational_reference", "high", ("sanitation", "changeover")),
    DepartmentKnowledgeEntry("kitchen", "changeover", "Allergen changeovers require discipline", "Weak changeover control increases cross-contact risk.", "Use signed changeover checklists for flagged runs.", "grounded_regulatory_theme", "high", ("allergen", "changeover")),
    DepartmentKnowledgeEntry("kitchen", "packaging dependency", "Packaging delays can signal upstream friction", "Frequent packaging_delay_flag can hide kitchen sequencing problems.", "Investigate batch handoff timing.", "heuristic_operational_pattern", "medium", ("packaging delay", "handoff")),
    DepartmentKnowledgeEntry("kitchen", "waste", "Waste-heavy runs need root-cause review", "Excess waste_units can indicate setup or formulation issues.", "Review waste by product_type and shift.", "heuristic_operational_pattern", "medium", ("waste", "batch")),
    DepartmentKnowledgeEntry("kitchen", "holds", "Hold concentration is an early warning", "Clusters of hold_flag batches reduce line confidence.", "Escalate hold root-cause trends weekly.", "grounded_operational_reference", "high", ("hold", "rework")),
    DepartmentKnowledgeEntry("kitchen", "throughput", "Production hours should map to output quality", "More hours with weaker pass rates indicates process drag.", "Pair throughput with quality metrics.", "heuristic_operational_pattern", "medium", ("production hours", "throughput")),
    DepartmentKnowledgeEntry("kitchen", "rework", "Rework concentration erodes capacity", "High rework_flag rates consume labor and delay release.", "Set rework thresholds by product type.", "heuristic_operational_pattern", "medium", ("rework", "capacity")),
    DepartmentKnowledgeEntry("kitchen", "execution", "Standardized batch records reduce drift", "Tight records improve diagnosis of dosage and QC issues.", "Require complete records for exception runs.", "grounded_operational_reference", "high", ("batch record", "standard work")),
    # Packaging
    DepartmentKnowledgeEntry("packaging", "label risk", "Label errors are major risk themes", "Label_error events can create recalls or holds.", "Escalate SKUs with recurring label_error_flag.", "grounded_regulatory_theme", "high", ("label", "error", "sku")),
    DepartmentKnowledgeEntry("packaging", "reconciliation", "Reconciliation variance needs fast triage", "Variance drift can signal counting or process controls issues.", "Track reconciliation_variance by line and shift.", "grounded_operational_reference", "high", ("reconciliation", "variance")),
    DepartmentKnowledgeEntry("packaging", "completion", "Slow completion often signals bottlenecks", "Low completion_rate by line/shift points to constraints.", "Benchmark line performance daily.", "heuristic_operational_pattern", "medium", ("completion", "line", "shift")),
    DepartmentKnowledgeEntry("packaging", "scrap", "Scrap concentration signals instability", "Scrap-heavy lots often correlate with setup or training gaps.", "Escalate scrap hotspots by operator.", "heuristic_operational_pattern", "medium", ("scrap", "operator")),
    DepartmentKnowledgeEntry("packaging", "holds", "Packaging holds distort downstream inventory", "Hold queues slow order readiness and create planning noise.", "Monitor hold aging and root causes.", "grounded_operational_reference", "high", ("hold", "aging")),
    DepartmentKnowledgeEntry("packaging", "rework", "Rework-heavy SKUs need redesign", "Repeated rework can indicate packaging spec or SOP mismatch.", "Create SKU-level corrective plans.", "heuristic_operational_pattern", "medium", ("rework", "sku")),
    DepartmentKnowledgeEntry("packaging", "line balance", "Line balancing improves flow", "Uneven line utilization amplifies bottlenecks.", "Redistribute work by completion profile.", "heuristic_operational_pattern", "medium", ("line", "balance", "flow")),
    DepartmentKnowledgeEntry("packaging", "shift variance", "Shift variance should be explicit", "One shift repeatedly underperforming suggests training/process gaps.", "Audit shift-level adherence.", "heuristic_operational_pattern", "medium", ("shift", "variance")),
    DepartmentKnowledgeEntry("packaging", "operator stability", "Operator consistency protects quality", "Large operator spread often predicts quality events.", "Use targeted coaching by operator trends.", "grounded_operational_reference", "high", ("operator", "consistency")),
    DepartmentKnowledgeEntry("packaging", "throughput quality", "Speed without quality is false efficiency", "High output with high errors increases downstream cost.", "Pair throughput with error metrics.", "grounded_operational_reference", "high", ("throughput", "quality")),
    # Compliance
    DepartmentKnowledgeEntry("compliance", "repeat issues", "Repeat issues matter more than one-offs", "Recurring issue types usually indicate control gaps.", "Track recurrence by issue_type and department.", "grounded_regulatory_theme", "high", ("repeat", "issue")),
    DepartmentKnowledgeEntry("compliance", "capa aging", "Aging CAPAs are pressure signals", "Open corrective actions that age out increase operational risk.", "Escalate open_days outliers quickly.", "grounded_regulatory_theme", "high", ("capa", "open days", "corrective")),
    DepartmentKnowledgeEntry("compliance", "training", "Training gaps underlie repeat failures", "training_gap_flag clusters often precede issue recurrence.", "Pair CAPA with retraining plans.", "grounded_operational_reference", "high", ("training", "gap")),
    DepartmentKnowledgeEntry("compliance", "state context", "State references should inform, not overstate", "Use state references for context without giving legal advice.", "Surface official links and conservative guidance.", "grounded_regulatory_theme", "high", ("state", "reference", "legal")),
    DepartmentKnowledgeEntry("compliance", "labeling", "Labeling issues can cascade quickly", "Labeling gaps often create packaging and distribution risk.", "Prioritize recurring labeling_flag events.", "grounded_regulatory_theme", "high", ("labeling", "packaging")),
    DepartmentKnowledgeEntry("compliance", "tracking", "Tracking inconsistencies are high-priority", "Tracking events can signal reconciliation weaknesses.", "Review tracking_flag trends by department.", "grounded_regulatory_theme", "high", ("tracking", "reconciliation")),
    DepartmentKnowledgeEntry("compliance", "testing", "Testing failures require cross-functional response", "testing_flag events can originate upstream in ops.", "Route testing trends back to source departments.", "grounded_operational_reference", "high", ("testing", "quality")),
    DepartmentKnowledgeEntry("compliance", "transport", "Transport flags expose handoff risk", "transport_flag patterns often point to handoff SOP issues.", "Audit manifest/handoff checkpoints.", "grounded_regulatory_theme", "high", ("transport", "handoff")),
    DepartmentKnowledgeEntry("compliance", "severity", "Severity-weighted triage improves focus", "High-severity issues should drive review cadence.", "Triage by severity before raw volume.", "heuristic_operational_pattern", "medium", ("severity", "triage")),
    DepartmentKnowledgeEntry("compliance", "department pressure", "Issue concentration by department matters", "One department driving most issues signals localized control gaps.", "Set departmental risk ownership.", "heuristic_operational_pattern", "medium", ("department", "concentration")),
    # Retail ops
    DepartmentKnowledgeEntry("retail_ops", "category mix", "Category imbalance can create store friction", "Overweight categories can suppress customer flow and turns.", "Review category share versus customer demand.", "heuristic_operational_pattern", "medium", ("category", "mix", "friction")),
    DepartmentKnowledgeEntry("retail_ops", "slow segments", "Slow segments drag experience", "Persistent low movement categories can clutter shelves.", "Use simplification and rotation plans.", "heuristic_operational_pattern", "medium", ("slow", "segments")),
    DepartmentKnowledgeEntry("retail_ops", "assortment", "Over-complex assortment hurts shopability", "Too many similar SKUs can reduce conversion clarity.", "Consolidate duplicate price-positioned items.", "heuristic_operational_pattern", "medium", ("assortment", "shopability")),
    DepartmentKnowledgeEntry("retail_ops", "pricing", "Pricing clutter confuses staff and guests", "Incoherent ladders reduce upsell and confidence.", "Rationalize price bands by category.", "heuristic_operational_pattern", "medium", ("pricing", "ladder")),
    DepartmentKnowledgeEntry("retail_ops", "ops cadence", "Consistent floor execution matters", "Execution cadence impacts conversion and throughput.", "Standardize daily store checks.", "grounded_operational_reference", "high", ("execution", "store")),
    DepartmentKnowledgeEntry("retail_ops", "promotion", "Promotion depth needs guardrails", "Over-discounting can erode margin without lift.", "Tie promotions to clear objectives.", "heuristic_operational_pattern", "medium", ("promotion", "margin")),
    DepartmentKnowledgeEntry("retail_ops", "staffing", "Staffing mismatches distort throughput", "Queue congestion and missed engagement reduce conversion.", "Map staffing to demand windows.", "grounded_operational_reference", "high", ("staffing", "throughput")),
    DepartmentKnowledgeEntry("retail_ops", "training", "Frontline training improves compliance and CX", "Knowledgeable staff reduce errors and increase trust.", "Use short, frequent training loops.", "grounded_operational_reference", "high", ("training", "cx", "compliance")),
    DepartmentKnowledgeEntry("retail_ops", "inventory", "Shelf availability drives performance", "Stockouts and overstock can both degrade experience.", "Align replenishment with movement.", "heuristic_operational_pattern", "medium", ("inventory", "replenishment")),
    DepartmentKnowledgeEntry("retail_ops", "simplicity", "Operational simplicity compounds", "Simpler operating models improve consistency under pressure.", "Reduce optional complexity in daily tasks.", "heuristic_operational_pattern", "medium", ("simplicity", "consistency")),
    # Executive
    DepartmentKnowledgeEntry("executive", "cross-functional", "Cross-functional bottlenecks deserve priority", "Department handoff friction often drives compounding delays.", "Track where one team blocks another.", "grounded_operational_reference", "high", ("cross-functional", "bottleneck")),
    DepartmentKnowledgeEntry("executive", "recurring risk", "Recurring risks beat one-off noise", "Repeat signals indicate systemic, not isolated, problems.", "Prioritize recurring themes in reviews.", "grounded_operational_reference", "high", ("recurring", "risk")),
    DepartmentKnowledgeEntry("executive", "actionability", "Decision-ready summaries should stay concise", "Operational detail is useful only if tied to decisions.", "Frame updates as risk, impact, next action.", "heuristic_operational_pattern", "medium", ("summary", "decision")),
    DepartmentKnowledgeEntry("executive", "dependency", "Downstream issues often start upstream", "Packaging or compliance stress may originate in kitchen/extraction/cultivation.", "Trace root causes across handoffs.", "heuristic_operational_pattern", "medium", ("downstream", "upstream")),
    DepartmentKnowledgeEntry("executive", "cadence", "Weekly cadence beats ad hoc firefighting", "Stable review cadence reduces delayed escalations.", "Use fixed cross-functional risk cadence.", "grounded_operational_reference", "high", ("cadence", "review")),
    DepartmentKnowledgeEntry("executive", "capacity", "Capacity risk is multi-departmental", "One constrained function can flatten total output.", "Watch constraint migration across teams.", "heuristic_operational_pattern", "medium", ("capacity", "constraint")),
    DepartmentKnowledgeEntry("executive", "quality", "Quality drift has compounding cost", "Small quality instability can ripple into rework and compliance burden.", "Escalate repeat quality drift early.", "grounded_operational_reference", "high", ("quality", "rework")),
    DepartmentKnowledgeEntry("executive", "compliance posture", "Compliance posture affects operating flexibility", "Aging issues or repeat flags reduce strategic room.", "Treat compliance lag as strategic risk.", "grounded_regulatory_theme", "high", ("compliance", "strategic")),
    DepartmentKnowledgeEntry("executive", "signal clarity", "Avoid metric overload", "Too many indicators can hide the true bottleneck.", "Limit scorecards to key risk/action metrics.", "heuristic_operational_pattern", "medium", ("metrics", "focus")),
    DepartmentKnowledgeEntry("executive", "ownership", "Risk ownership should be explicit", "Named owners improve closure speed and accountability.", "Assign owners to recurring themes.", "grounded_operational_reference", "high", ("ownership", "accountability")),
)


def get_department_knowledge(department: str) -> list[dict]:
    dept = (department or "").strip().lower()
    out=[]
    for entry in _ENTRIES:
        if entry.department == dept:
            item=asdict(entry)
            item["keywords"]=list(item.get("keywords", []))
            out.append(item)
    return out


def search_department_knowledge(department: str, question: str, limit: int = 5) -> list[dict]:
    dept_entries = get_department_knowledge(department)
    q = (question or "").lower()
    scored: list[tuple[int, dict]] = []
    for entry in dept_entries:
        score = 0
        if entry["topic"] in q:
            score += 2
        for kw in entry["keywords"]:
            if kw in q:
                score += 2
        if entry["trust_level"] == "high":
            score += 1
        scored.append((score, entry))
    scored.sort(key=lambda item: item[0], reverse=True)
    matches = [entry for score, entry in scored if score > 0]
    return matches[:limit] if matches else dept_entries[:limit]


def render_department_knowledge_summary(matches: list[dict]) -> str:
    if not matches:
        return "No built-in department knowledge matches available."
    lines = ["Built-in learned knowledge (curated, conservative):"]
    for entry in matches[:5]:
        lines.append(f"- {entry['title']}: {entry['summary']} Guidance: {entry['guidance']} ({entry['source_type']}, {entry['trust_level']}).")
    return "\n".join(lines)
