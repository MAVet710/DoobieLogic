from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PackagingRecord:
    lot_id: str
    sku: str
    units_packed: float
    packaging_hours: float
    label_error_flag: bool
    packaging_hold_flag: bool
    reconciliation_variance: float
    scrap_units: float
    operator: str
    line: str
    shift: str
    completion_rate: float
    rework_flag: bool
