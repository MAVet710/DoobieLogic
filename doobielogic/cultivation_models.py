from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CultivationRecord:
    strain: str
    room: str
    phase: str
    canopy_sqft: float
    plant_count: int
    expected_yield_g: float
    actual_yield_g: float
    waste_g: float
    test_pass_rate: float
    cycle_days: float
    harvest_date: str
    moisture_risk_flag: bool
    microbial_risk_flag: bool
