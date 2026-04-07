from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExtractionRecord:
    batch_id: str
    input_material_type: str
    input_weight_g: float
    output_type: str
    output_weight_g: float
    yield_pct: float
    pass_fail: str
    residual_solvent_flag: bool
    terpene_retention_pct: float
    turnaround_hours: float
    downtime_minutes: float
    operator: str
    batch_status: str
    rework_flag: bool
