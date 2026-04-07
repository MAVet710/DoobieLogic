from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ComplianceRecord:
    issue_id: str
    issue_type: str
    department: str
    severity: str
    corrective_action_status: str
    open_days: float
    repeat_issue_flag: bool
    state: str
    source_type: str
    packaging_flag: bool
    tracking_flag: bool
    labeling_flag: bool
    testing_flag: bool
    transport_flag: bool
    training_gap_flag: bool
