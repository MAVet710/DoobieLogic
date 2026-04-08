from __future__ import annotations


DEPARTMENT_HEADER_HINTS = {
    "cultivation": {"strain", "room", "cycle_days", "microbial_risk_flag", "expected_yield_g"},
    "extraction": {"batch_id", "yield_pct", "residual_solvent_flag", "downtime_minutes", "output_type"},
    "kitchen": {"dosage_variance_pct", "qc_pass_rate", "allergen_changeover_flag", "sanitation_gap_flag"},
    "packaging": {"lot_id", "completion_rate", "reconciliation_variance", "label_error_flag"},
    "compliance": {"issue_id", "corrective_action_status", "repeat_issue_flag", "open_days", "severity"},
    "retail_ops": {"product", "category", "price", "quantity", "revenue", "inventory"},
}


def detect_department_from_headers(headers: list[str]) -> str:
    normalized = {str(h).strip().lower() for h in headers}
    best_dept = "retail_ops"
    best_score = 0
    for dept, hints in DEPARTMENT_HEADER_HINTS.items():
        score = len(normalized.intersection({h.lower() for h in hints}))
        if score > best_score:
            best_score = score
            best_dept = dept
    return best_dept
