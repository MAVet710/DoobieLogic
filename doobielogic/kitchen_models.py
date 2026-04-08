from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KitchenRecord:
    batch_id: str
    product_name: str
    product_type: str
    batch_size_units: float
    expected_dosage_mg: float
    actual_dosage_mg: float
    dosage_variance_pct: float
    qc_pass_rate: float
    rework_flag: bool
    waste_units: float
    allergen_changeover_flag: bool
    sanitation_gap_flag: bool
    production_hours: float
    packaging_delay_flag: bool
    hold_flag: bool
