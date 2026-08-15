from __future__ import annotations

from typing import Any

from doobielogic.professional_domains import professional_domain_result


def _result(
    *,
    mode: str,
    answer: str,
    recommendations: list[str],
    confidence: str = "medium",
    risks: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "answer": answer,
        "explanation": (
            "This is a diagnostic operating playbook, not a conclusion about your facility. "
            "Use the requested records to confirm the cause before changing a controlled process."
        ),
        "recommendations": recommendations,
        "confidence": confidence,
        "sources": [f"[module_curriculum:{mode}]"],
        "mode": mode,
        "routed_mode": mode,
        "risk_flags": risks or [],
        "inefficiencies": [],
    }


def answer_operational_question(question: str, mode: str) -> dict[str, Any] | None:
    """Return a useful deterministic baseline for common cannabis-operations questions."""

    q = str(question or "").strip().casefold()

    if any(term in q for term in ("basket size", "average transaction", "atv", "units per transaction")):
        return _result(
            mode="retail_ops",
            answer=(
                "Decompose the drop into traffic, conversion, units per transaction, average item price, "
                "discount rate, and stockouts by hour. The manager should first compare yesterday with the "
                "same weekday and identify whether fewer items, lower-priced mix, or deeper discounts caused it."
            ),
            recommendations=[
                "Review hourly transactions, units, net sales, discounts, returns, and top-SKU availability.",
                "Check whether a promotion, menu outage, queue spike, or staffing gap changed customer behavior.",
                "Coach one observable behavior at a time, then recheck ATV and margin on the next comparable shift.",
            ],
        )

    if "budtender" in q and any(term in q for term in ("attach", "coach", "training", "upsell")):
        return _result(
            mode="retail_ops",
            answer=(
                "Coach compliant discovery and category pairing, not medical outcomes: ask what format, "
                "experience, budget, and occasion the customer prefers, then offer one relevant add-on with "
                "clear product facts and no disease or treatment claim."
            ),
            recommendations=[
                "Use short role-play sessions built from approved product information and prohibited-claims examples.",
                "Track attach rate with returns, complaints, discounting, and mystery-shop qualityâ€”not sales alone.",
                "Have compliance approve the language guide for the applicable jurisdiction.",
            ],
            risks=["Unapproved health or therapeutic claims can create regulatory and consumer-safety exposure."],
        )

    if "vendor" in q and any(term in q for term in ("discount", "deal", "double", "moq", "minimum order")):
        return _result(
            mode="buyer",
            answer=(
                "The discount is only a good deal if the incremental units will sell before they age and the "
                "cash return beats the carrying risk. Compare landed gross profit, weeks of supply after the buy, "
                "sell-through, case-pack exposure, payment terms, and likely markdowns."
            ),
            recommendations=[
                "Model the normal order and discounted order using conservative weekly velocity.",
                "Reject or renegotiate if the larger buy breaches your category days-on-hand or cash limit.",
                "Ask for split deliveries, better terms, or a smaller MOQ before taking excess inventory.",
            ],
            confidence="low",
            risks=["Headline margin can hide aging, markdown, and working-capital cost."],
        )

    if any(term in q for term in ("reorder", "how much should i buy", "order quantity")):
        return _result(
            mode="buyer",
            answer=(
                "Reorder only the SKUs projected to fall below safety stock before the next reliable receipt. "
                "A practical quantity is target stock minus available inventory minus inbound purchase orders, "
                "using recent demand adjusted for trend, seasonality, promotions, and vendor lead time."
            ),
            recommendations=[
                "Provide SKU/location sales history, available on hand, open POs, lead time, case pack, and target service level.",
                "Cap quantities where the resulting days on hand exceeds the category aging threshold.",
                "Protect proven velocity and assortment gaps before adding speculative long-tail inventory.",
            ],
            confidence="low",
        )

    if any(term in q for term in ("dead stock", "at risk of expiring", "aging inventory", "inventory is at risk")):
        return _result(
            mode="buyer",
            answer=(
                "Rank inventory by days on hand, recent sell-through, days since last sale, package or test dates, "
                "remaining compliant shelf life, open purchase orders, and gross-margin dollars at risk. Start with "
                "high-value lots that have weak velocity and the shortest remaining disposition window."
            ),
            recommendations=[
                "Segment by SKU, lot/package, location, age bucket, and weeks of supply.",
                "Cancel or reduce inbound POs before adding markdowns, transfers, bundles, or other approved exit actions.",
                "Track each action against recovered cash, margin loss, and units ultimately destroyed or written off.",
            ],
            confidence="low",
            risks=["Disposition, transfer, promotion, and destruction options must follow jurisdiction and license rules."],
        )

    if any(term in q for term in ("slow mover", "slow-moving", "markdown")):
        return _result(
            mode="buyer",
            answer=(
                "Rank markdown candidates by weeks of supply, recent velocity, days since last sale, package age, "
                "remaining shelf life, gross-profit dollars at risk, and inbound commitments. Use the smallest "
                "approved price action likely to restore sell-through while protecting cash recovery."
            ),
            recommendations=[
                "Cancel or reduce open purchase orders and check compliant transfers before discounting existing inventory.",
                "Test a documented markdown ladder by age and velocity instead of applying one blanket percentage.",
                "Measure unit lift, incremental gross profit, cash recovered, cannibalization, and remaining aged units after each step.",
            ],
            confidence="low",
            risks=["Promotion, discount, transfer, donation, return, and destruction options vary by jurisdiction and agreement."],
        )

    if any(term in q for term in ("negative on-hand", "negative on hand", "unexplained inventory adjustment")):
        return _result(
            mode="buyer",
            answer=(
                "Treat the variance as an inventory-control incident: preserve the audit trail, stop repeated "
                "manual corrections, perform a witnessed physical count, and reconcile receipts, transfers, "
                "sales, voids, returns, waste, and track-and-trace events in timestamp order."
            ),
            recommendations=[
                "Record the affected item, lot/package ID, user, terminal, timestamp, reason code, and before/after quantity.",
                "Restrict the account if misuse is plausible while management reviews access logs and camera coverage.",
                "Correct the system only through the approved adjustment workflow and document root cause and CAPA.",
            ],
            risks=["Do not destroy or overwrite audit evidence; reporting duties vary by jurisdiction."],
        )

    if mode == "cultivation" and any(term in q for term in ("yield", "underperform", "compare cultivar", "cultivar performance")):
        return _result(
            mode="cultivation",
            answer=(
                "Compare the result within matched cultivar-room-cycle cohorts. Check sellable grams per canopy "
                "area, plant count and survival, cycle days, environmental and irrigation exceptions, pest or "
                "microbial events, harvest moisture, dry/cure loss, test pass rate, and waste before changing genetics."
            ),
            recommendations=[
                "Build a room-by-cultivar trend for at least three comparable harvests.",
                "Reconcile wet weight, dry weight, packaged weight, testing loss, and recorded waste as a mass balance.",
                "Audit SOP adherence and sensor exceptions for the first process step where the variance appears.",
            ],
            risks=["Do not prescribe pesticide, nutrient, or remediation changes without label, SOP, and jurisdiction review."],
        )

    if mode == "cultivation" and any(term in q for term in ("powdery mildew", "botrytis", "pest", "disease", "humidity")):
        return _result(
            mode="cultivation",
            answer=(
                "Contain the affected room today: restrict traffic and tool movement, flag and map symptomatic plants, "
                "protect unaffected rooms, and place potentially affected harvest material on quality hold. Verify the "
                "humidity excursion and leaf-surface conditions with calibrated sensors before changing the controlled process."
            ),
            recommendations=[
                "Map symptoms by room, bench, cultivar, plant stage, irrigation zone, and time; photograph and preserve scouting records.",
                "Review 24-hour temperature, relative humidity, dew-point or VPD trends, airflow, irrigation timing, leaks, sanitation, and recent room entries.",
                "Use only the facility IPM plan and products legally approved for the crop, site, growth stage, license, and jurisdiction.",
                "Escalate to cultivation, QA, and compliance owners to decide sampling, harvest hold, disposition, reporting, and CAPA.",
            ],
            risks=[
                "Do not apply an unapproved pesticide or conceal, trim around, remediate, or release affected material outside approved procedures."
            ],
        )

    if mode == "extraction" and any(term in q for term in ("yield", "hydrocarbon", "recovery", "residual solvent", "test failure")):
        residual = "residual" in q or "test failure" in q
        if residual:
            return _result(
                mode="extraction",
                answer=(
                    "Quarantine the affected lots and investigate the release failure before optimizing throughput. "
                    "Verify sample identity and COA, input lot and moisture, validated purge-cycle records, equipment "
                    "maintenance, solvent-recovery performance, operator/SOP adherence, and comparable passing runs."
                ),
                recommendations=[
                    "Open a deviation and preserve run, maintenance, sample-chain, and laboratory records.",
                    "Compare failed and passing lots by method, equipment, operator, input, and validated process checkpoints.",
                    "Use the approved SOP, equipment manufacturer limits, and qualified safety/compliance review for corrective action.",
                ],
                risks=["Do not improvise pressure, temperature, purge, or solvent settings from chatbot guidance."],
            )
        return _result(
            mode="extraction",
            answer=(
                "Start with a complete mass balance and compare matched runs. A 14% to 10% drop can come from "
                "input potency or moisture, unreconciled stage loss, recovery or downtime changes, equipment condition, "
                "operator setup, sampling, or a change in output specification."
            ),
            recommendations=[
                "Reconcile input mass, intermediate fractions, finished output, retained samples, waste, and solvent recovery.",
                "Compare the affected lot with passing runs using the same method, equipment, operator, and output type.",
                "Escalate safety, contamination, or failed-test signals before any yield optimization.",
            ],
            risks=["Process changes must remain inside validated SOP and manufacturer safety limits."],
        )

    if mode == "kitchen" and any(term in q for term in ("potency", "gummy", "homogeneity", "dosage")):
        return _result(
            mode="kitchen",
            answer=(
                "Quarantine the batch and trace potency variance through the concentrate assay and weighing, "
                "infusion preparation, mixing time and hold conditions, depositor consistency, cooling, sampling plan, "
                "and laboratory result. Determine whether the variation is in the product or the sample."
            ),
            recommendations=[
                "Reconcile theoretical potency to actual input assay, batch yield, unit count, and tested results.",
                "Compare samples by mixer/depositor position and time to detect segregation or settling.",
                "Review calibrated scales, batch records, in-process checks, sanitation, and changeover records before release.",
            ],
            risks=["Do not release, relabel, or rework a potency-variant batch without approved QA and regulatory procedures."],
        )

    if mode == "kitchen" and any(term in q for term in ("plan", "lead time", "schedule")):
        return _result(
            mode="kitchen",
            answer=(
                "Build the schedule backward from the required ship date and treat testing, QA disposition, "
                "label approval, and packaging capacity as release gatesâ€”not assumptions."
            ),
            recommendations=[
                "Use actual median and 90th-percentile lab turnaround, QA review, and packaging lead times.",
                "Reserve packaging slots by SKU and approved artwork version before the kitchen run starts.",
                "Keep a hold buffer and prohibit shipment planning from counting untested or unreleased units.",
            ],
        )

    if mode == "packaging" and any(term in q for term in ("mislabel", "label", "verification")):
        return _result(
            mode="packaging",
            answer=(
                "Stop and quarantine affected work, then redesign changeover around approved-artwork control, "
                "line clearance, product/lot-to-label matching, independent verification, barcode or vision checks, "
                "and final reconciliation before release."
            ),
            recommendations=[
                "Remove obsolete labels from the line and issue only the counted quantity for the scheduled SKU and lot.",
                "Require two-person or validated electronic verification at setup, first article, restart, and changeover.",
                "Reconcile issued, applied, damaged, returned, and destroyed labels and preserve the audit record.",
            ],
            risks=["A label or traceability mismatch can require a hold, investigation, notification, or recall."],
        )

    if mode == "packaging" and any(term in q for term in ("metric", "review daily", "line performance")):
        return _result(
            mode="packaging",
            answer=(
                "Review first-pass yield, units per labor hour, schedule attainment, downtime by cause, changeover time, "
                "scrap and rework, label-error rate, reconciliation variance, completion rate, and hold age together."
            ),
            recommendations=[
                "Segment every metric by line, shift, SKU, lot, and operator; totals can hide the constraint.",
                "Set an owner and same-shift escalation threshold for label, traceability, and reconciliation errors.",
                "Pair speed with quality so high output with high rework is not treated as success.",
            ],
        )

    if any(term in q for term in ("gross margin fell", "margin fell", "margin decline")):
        return _result(
            mode="executive",
            answer=(
                "Bridge the five-point decline into price, discount, category/SKU mix, unit cost, freight, vendor funding, "
                "shrink/write-offs, and inventory-accounting effects. Then separate true margin erosion from a mix shift."
            ),
            recommendations=[
                "Compare this month with the prior month and same month last year at category, vendor, brand, and location level.",
                "Quantify the point impact of each driver and assign owners to the top two controllable causes.",
                "Check whether discount-driven volume improved gross profit dollars, inventory turns, and cashâ€”not margin rate alone.",
            ],
        )

    if any(term in q for term in ("how many budtenders", "staffing", "schedule friday")):
        return _result(
            mode="ops",
            answer=(
                "Calculate staffing from forecast transactions by 15-minute interval, average service minutes, "
                "target utilization, required fixed posts, breaks, and local supervision/security rules. I need those "
                "inputs to give a responsible headcount."
            ),
            recommendations=[
                "Forecast traffic and transactions from comparable Fridays, promotions, events, and payday effects.",
                "Convert workload to concurrent labor, then add fixed reception/ID, pickup, floor, and manager coverage.",
                "Validate the plan against target wait time and adjust after measuring actual arrivals and service time.",
            ],
            confidence="low",
        )

    if mode == "executive" and any(term in q for term in ("agenda", "weekly operating review", "operating review")):
        return _result(
            mode="executive",
            answer=(
                "Run a 60-minute exception-based review: safety/compliance and quality holds; sales, margin, and cash; "
                "inventory and purchasing; cultivation/production output; testing and release; retail/service; people/capacity; "
                "then decisions, owners, due dates, and unresolved risks."
            ),
            recommendations=[
                "Use one scorecard with targets, actuals, trend, owner, and red/yellow/green status.",
                "Discuss only material exceptions and cross-functional blockers; move routine detail to department reviews.",
                "End with a decision log and review last week's commitments before accepting new ones.",
            ],
        )

    if mode == "ops" and any(term in q for term in ("bottleneck", "throughput", "workflow", "capacity")):
        return _result(
            mode="ops",
            answer=(
                "Map the work from released input to released output and measure queue time, touch time, first-pass "
                "yield, downtime, changeover, staffing, and work-in-process at each step. The constraint is the step "
                "whose sustainable capacity and availability limit total flowâ€”not necessarily the busiest station."
            ),
            recommendations=[
                "Timestamp arrivals, starts, completions, holds, rework, and handoffs for a representative production window.",
                "Protect the constraint from starvation and blocking, move nonessential work away from it, and control upstream release.",
                "After improvement, remeasure total lead time and throughput because the constraint may move elsewhere.",
            ],
        )

    if "wait time" in q and "id" in q:
        return _result(
            mode="retail_ops",
            answer=(
                "Separate arrival and ID verification from product consultation, pre-stage compliant pickup orders, "
                "and staff to interval demand. Measure each queue stage so you fix the actual constraint."
            ),
            recommendations=[
                "Track arrival-to-ID, ID-to-service, consultation, payment, and pickup times by 15-minute interval.",
                "Use approved ID-scanning and privacy procedures for the jurisdiction and keep a manual exception path.",
                "Create express pickup and reception roles only where volume data shows they reduce total wait.",
            ],
            risks=["ID acceptance, data retention, and customer privacy requirements vary by jurisdiction."],
        )

    if mode == "quality" and any(term in q for term in ("complaint", "recall", "quarantine", "release")):
        return _result(
            mode="quality",
            answer=(
                "Contain the affected lots first, preserve complaint and distribution evidence, and run a documented "
                "health-hazard and scope assessment. Trace the issue across related lots, inputs, equipment, shifts, "
                "test results, changes, and destinations before deciding release, withdrawal, or recall."
            ),
            recommendations=[
                "Log the complaint with product, lot, date, location, symptoms or defect, photos, and remaining sample details.",
                "Reconcile inventory and distribution by lot, place appropriate holds, and define the potentially affected population.",
                "Use the approved escalation, regulator-notification, recall, effectiveness-check, and CAPA procedures.",
            ],
            risks=["Do not release held product or contact consumers or regulators outside the approved quality and legal process."],
        )

    if mode == "laboratory" and any(term in q for term in ("oos", "out of specification", "retest", "lab result")):
        return _result(
            mode="laboratory",
            answer=(
                "Treat the result as reportable and the product as controlled unless an authorized investigation proves "
                "a valid assignable laboratory cause. Preserve raw data and audit trails, verify sample identity and chain "
                "of custody, review method controls and instrument performance, then investigate the production batch."
            ),
            recommendations=[
                "Open the OOS investigation and retain the original preparation, chromatograms, calculations, standards, and audit trail.",
                "Review sampling plan, chain of custody, analyst steps, method version, controls, calibration, integration, and system suitability.",
                "Retest or resample only when the approved procedure and jurisdiction permit it, with a written rationale established in advance.",
            ],
            risks=["Do not average away a failure, discard unfavorable data, or repeat testing until a passing result appears."],
        )

    if mode == "distribution" and any(term in q for term in ("manifest", "delivery", "shipment", "wholesale", "otif")):
        if "manifest" in q and any(term in q for term in ("mismatch", "does not match", "doesn't match", "incorrect", "wrong")):
            return _result(
                mode="distribution",
                answer=(
                    "Do not continue the transfer as though the records match. Stop at the safest authorized location, "
                    "maintain custody and security, preserve the original manifest and traceability audit trail, and have "
                    "an authorized employee resolve the physical-versus-system discrepancy under the jurisdiction's current procedure."
                ),
                recommendations=[
                    "Count and identify every physical package without altering identifiers, then compare package ID, quantity, lot, origin, destination, vehicle, personnel, and timestamps.",
                    "Contact the dispatch, receiving, compliance, and traceability owners through approved channels and record instructions and times.",
                    "Correct, void, return, or regenerate records only through an authorized workflow; document custody, root cause, and final reconciliation.",
                ],
                risks=["Do not edit records to fit the load, make an unauthorized stop, deliver mismatched product, or break chain of custody."],
            )
        return _result(
            mode="distribution",
            answer=(
                "Release and allocate the order by lot first, then verify the receiving license, delivery window, "
                "vehicle and authorized personnel, required manifest fields, package quantities, route, security plan, "
                "and proof-of-delivery workflow. Reconcile every exception before inventory is made available again."
            ),
            recommendations=[
                "Match sales order, released lots, traceability packages, physical counts, and destination authorization before loading.",
                "Record custody handoffs, departure and arrival evidence, quantity accepted or refused, damages, and return disposition.",
                "Review OTIF, fill rate, route cost, delivery exceptions, days sales outstanding, and returns by customer.",
            ],
            risks=["Transport, route, vehicle, manifest, timing, and return rules are jurisdiction-specific and require current verification."],
        )

    if mode == "security" and any(term in q for term in ("data breach", "ransomware", "cybersecurity", "employee account")):
        return _result(
            mode="security",
            answer=(
                "Activate the incident plan: preserve evidence, isolate affected systems through authorized IT controls, "
                "disable compromised credentials, protect backups and traceability continuity, and establish an incident "
                "timeline. Do not erase or rebuild systems until forensic and notification needs are assessed."
            ),
            recommendations=[
                "Identify affected accounts, devices, data, vendors, locations, and the earliest known malicious activity.",
                "Use clean communications, rotate privileged credentials, verify backups, and maintain a documented manual-operations plan.",
                "Have privacy, legal, insurance, law-enforcement, regulator, and customer notifications assessed against applicable deadlines.",
            ],
            risks=["Do not pay, negotiate, disclose, or destroy evidence without authorized legal, insurance, and incident-response guidance."],
        )

    if mode == "security" and any(term in q for term in ("theft", "diversion", "cash", "camera", "alarm", "access")):
        return _result(
            mode="security",
            answer=(
                "Protect people first, restrict access to the affected area or records, preserve video and access logs, "
                "and reconcile physical inventory or cash to traceability and POS records. Document who knew what and "
                "when, without conducting an unsafe confrontation."
            ),
            recommendations=[
                "Preserve camera, alarm, access-control, safe, POS, traceability, schedule, and visitor records for the full relevant window.",
                "Use two-person counts and chain-of-custody controls while calculating the exact variance and affected packages or drawers.",
                "Follow approved escalation and determine current regulator, law-enforcement, insurer, and labor requirements.",
            ],
            risks=["Never confront a suspected person or alter surveillance, access, cash, or traceability evidence."],
        )

    if mode == "finance" and any(term in q for term in ("accounts receivable", "collections", "cash flow", "cash forecast", "working capital")):
        return _result(
            mode="finance",
            answer=(
                "Build a rolling 13-week cash forecast from bank balance, collectible receivables, committed purchasing, "
                "payroll, tax, debt, rent, and essential operating payments. Age receivables by customer and dispute status, "
                "then prioritize collection actions by cash impact and relationship risk."
            ),
            recommendations=[
                "Reconcile opening cash to bank records and assign confidence and owner to every expected receipt and payment.",
                "Segment receivables into current, disputed, promised, late, and high-risk; document next action and date for each.",
                "Stress-test slower collections, inventory commitments, taxes, and minimum operating cash before approving discretionary spend.",
            ],
            risks=["Cannabis tax, banking, cash-handling, and insolvency decisions require qualified accounting and legal review."],
        )

    if mode == "finance" and any(term in q for term in ("cash is tight", "cash is low", "cash runway", "liquidity")):
        return _result(
            mode="finance",
            answer=(
                "Protect the next 13 weeks of payroll, tax, rent, debt, required compliance, and continuity-critical cash first. "
                "Freeze speculative buys, reduce or cancel uncommitted inbound inventory, accelerate collectible receivables, "
                "and create a controlled plan for aging stock that measures cash recovered after discount and disposition cost."
            ),
            recommendations=[
                "Reconcile bank cash today and build a weekly base, downside, and severe-downside forecast with an owner and confidence for every receipt and payment.",
                "Rank aged inventory by cash tied up, sell-through, package age, shelf-life or disposition window, margin after action, and open purchase commitments.",
                "Approve purchasing against a cash cap and minimum operating reserve; protect proven velocity and required assortment before long-tail inventory.",
                "Assign collection actions to every overdue receivable and negotiate payment timing or split deliveries before creating a critical default.",
            ],
            confidence="low",
            risks=["Tax, insolvency, banking, promotion, transfer, return, and destruction decisions require current accounting, legal, and jurisdiction review."],
        )

    if mode == "people" and any(term in q for term in ("onboarding", "training", "new hire", "hiring")):
        return _result(
            mode="people",
            answer=(
                "Use role-based qualification, not attendance alone. Map each role to required licenses, policies, SOPs, "
                "safety and security duties, systems access, supervised practice, and observed competency before independent work."
            ),
            recommendations=[
                "Create a training matrix with role, requirement, trainer, due date, version, assessment, expiry, and evidence location.",
                "Stage access so POS, traceability, production, inventory, security, and admin permissions follow verified qualification.",
                "Use 7-, 30-, and 60-day check-ins to close skill gaps and confirm the employee can execute critical tasks.",
            ],
            risks=["Age, background-check, credential, labor, privacy, and training requirements vary by role and jurisdiction."],
        )

    if mode == "maintenance" and any(term in q for term in ("downtime", "failure", "maintenance", "work order", "spares")):
        return _result(
            mode="maintenance",
            answer=(
                "Place the equipment in a safe state and protect affected product, then distinguish the failure symptom "
                "from its cause. Review alarms, operating conditions, recent work and changeovers, calibration, utilities, "
                "wear parts, and repeat history before returning the asset to service."
            ),
            recommendations=[
                "Record asset, time, symptom, product impact, safe-state action, error codes, operator, and conditions in the work order.",
                "Use failure history and consequence to set preventive tasks, frequencies, condition checks, and critical-spares levels.",
                "Require documented repair verification, calibration where applicable, sanitation or line clearance, and authorized return to service.",
            ],
            risks=["Do not bypass interlocks or prescribe electrical, pressure, solvent, gas, or mechanical repairs without qualified personnel."],
        )

    if mode == "marketing" and any(term in q for term in ("campaign", "promotion", "loyalty", "advertising", "marketing")):
        return _result(
            mode="marketing",
            answer=(
                "Evaluate incremental gross profit, not redemption alone. Define the eligible audience and holdout, approved "
                "message, total discount and media cost, baseline behavior, inventory capacity, and compliance review before launch."
            ),
            recommendations=[
                "Track reach, conversion, incremental transactions, basket, margin after discount, repeat rate, unsubscribes, and complaints.",
                "Separate customers who would have purchased anyway from truly incremental demand using a holdout or matched comparison.",
                "Archive audience criteria, creative version, approvals, channel consent, offer rules, and results.",
            ],
            risks=["Age gating, health claims, audience targeting, discounts, loyalty, SMS, and advertising placement rules vary by jurisdiction."],
        )

    if mode == "product_development" and any(term in q for term in ("new product", "prototype", "scale-up", "launch", "stability")):
        return _result(
            mode="product_development",
            answer=(
                "Use gated development: consumer and business need, regulatory feasibility, target product profile, "
                "bench prototype, safety and compatibility review, pilot, scale-up, validated specifications, stability, "
                "packaging and label approval, cost and capacity confirmation, then controlled launch."
            ),
            recommendations=[
                "Define dose or potency target, ingredients and allergens, sensory attributes, package, shelf life, COGS, and acceptance criteria.",
                "Document every formulation and process version; compare theoretical and actual yield, potency, uniformity, and waste at each scale.",
                "Do not commit launch inventory until testing, QA release, artwork, sourcing, capacity, and jurisdiction requirements clear their gates.",
            ],
            risks=["Do not infer safety, shelf life, homogeneity, compatibility, or compliant claims from a successful small prototype."],
        )

    if mode == "ehs" and any(term in q for term in ("injury", "exposure", "near miss", "hazard", "ppe", "sds")):
        return _result(
            mode="ehs",
            answer=(
                "Provide emergency care and stop or isolate the hazard first. Preserve the scene when safe, identify "
                "the task and energy or chemical sources, collect witness and equipment evidence, and investigate system "
                "causes without blaming the injured person."
            ),
            recommendations=[
                "Record who, what, when, where, task, conditions, exposure, controls, training, witnesses, and immediate actions.",
                "Use the hierarchy of controls: eliminate, substitute, engineer, administrate, then PPE; verify effectiveness after correction.",
                "Assess occupational, fire, environmental, workers-compensation, and regulator reporting with qualified personnel.",
            ],
            risks=["For an active emergency, evacuate or call emergency services under the facility plan; chatbot guidance is not emergency response."],
        )

    if mode == "ehs" and any(term in q for term in ("energy", "water", "environmental", "sustainability")):
        return _result(
            mode="ehs",
            answer=(
                "Normalize utility use to production before choosing projects. Establish meter boundaries and a clean baseline, "
                "then separate weather, occupancy, canopy, batch volume, equipment schedule, leaks, and tariff effects."
            ),
            recommendations=[
                "Track electricity, demand, fuel, water, wastewater, and waste by site and production driver with cost and emissions factors.",
                "Prioritize leak repair, scheduling, controls, recommissioning, heat recovery, and reuse only after safety and quality review.",
                "Verify savings against the normalized baseline and include maintenance, product risk, incentives, and payback.",
            ],
            risks=["Utility, discharge, waste, emissions, and equipment changes require facility, permit, safety, and quality review."],
        )

    if mode == "copilot":
        return _result(
            mode="copilot",
            answer=(
                "Start with the largest exception that can harm people, license status, product quality, cash, or "
                "customer service. Review open compliance and safety events, quality holds, cash runway, aged inventory, "
                "service failures, production constraints, and overdue owner commitments; then choose no more than three priorities."
            ),
            recommendations=[
                "List each exception with impact, evidence, owner, due date, and the decision that is currently blocked.",
                "Escalate immediate safety, diversion, contamination, failed-test, recall, cybersecurity, or license risks first.",
                "Give me your role, jurisdiction, top goal, and current numbers or records, and I will turn them into a focused action plan.",
            ],
            confidence="low",
        )

    return professional_domain_result(question, mode)
