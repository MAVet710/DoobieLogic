from __future__ import annotations

from datetime import date
from typing import Dict

from pydantic import BaseModel, Field, field_validator


class ProductMix(BaseModel):
    flower_pct: float = Field(ge=0, le=100)
    vape_pct: float = Field(ge=0, le=100)
    edible_pct: float = Field(ge=0, le=100)
    concentrate_pct: float = Field(ge=0, le=100)
    other_pct: float = Field(ge=0, le=100)

    @field_validator("other_pct")
    @classmethod
    def percentages_total_approx_100(cls, v: float, info):
        data = info.data
        values = [
            data.get("flower_pct", 0),
            data.get("vape_pct", 0),
            data.get("edible_pct", 0),
            data.get("concentrate_pct", 0),
            v,
        ]
        total = sum(values)
        if not (99.0 <= total <= 101.0):
            raise ValueError(f"product mix must total ~100, got {total:.2f}")
        return v


class CannabisInput(BaseModel):
    state: str = Field(min_length=2, max_length=2, description="US state code")
    period_start: date
    period_end: date
    total_sales_usd: float = Field(ge=0)
    transactions: int = Field(ge=0)
    units_sold: int = Field(ge=0)
    avg_basket_usd: float = Field(ge=0)
    inventory_days_on_hand: float = Field(ge=0)
    discount_rate_pct: float = Field(ge=0, le=100)
    price_per_gram_usd: float = Field(ge=0)
    active_retailers: int = Field(ge=0)
    license_violations: int = Field(ge=0)
    product_mix: ProductMix

    @field_validator("state")
    @classmethod
    def upper_state(cls, v: str) -> str:
        return v.upper()


class CannabisOutput(BaseModel):
    state: str
    score: float
    tier: str
    market_pressure: float
    compliance_risk: float
    inventory_stress: float
    recommendations: list[str]
    regulation_links: Dict[str, str]
