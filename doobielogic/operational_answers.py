from __future__ import annotations

from typing import Any


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
                "Track attach rate with returns, complaints, discounting, and mystery-shop quality—not sales alone.",
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
                "label approval, and packaging capacity as release gates—not assumptions."
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
                "Check whether discount-driven volume improved gross profit dollars, inventory turns, and cash—not margin rate alone.",
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

    return None
