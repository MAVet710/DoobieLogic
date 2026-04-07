from __future__ import annotations

from datetime import date
from typing import Any

from doobielogic.models import CannabisInput


def normalize_sales_rows_to_input(state: str, start_date: date, end_date: date, rows: list[dict[str, Any]]) -> CannabisInput:
    total_sales_usd = sum(float(r.get("sales_usd", 0) or 0) for r in rows)
    transactions = sum(int(r.get("transactions", 0) or 0) for r in rows)
    units_sold = sum(int(r.get("units_sold", 0) or 0) for r in rows)

    avg_basket_usd = total_sales_usd / transactions if transactions else 0.0

    flower = sum(float(r.get("flower_sales_usd", 0) or 0) for r in rows)
    vape = sum(float(r.get("vape_sales_usd", 0) or 0) for r in rows)
    edible = sum(float(r.get("edible_sales_usd", 0) or 0) for r in rows)
    concentrate = sum(float(r.get("concentrate_sales_usd", 0) or 0) for r in rows)
    other = max(total_sales_usd - (flower + vape + edible + concentrate), 0)

    def pct(v: float) -> float:
        return (v / total_sales_usd * 100) if total_sales_usd else 0.0

    return CannabisInput(
        state=state,
        period_start=start_date,
        period_end=end_date,
        total_sales_usd=total_sales_usd,
        transactions=transactions,
        units_sold=units_sold,
        avg_basket_usd=round(avg_basket_usd, 2),
        inventory_days_on_hand=_weighted_avg(rows, "inventory_days_on_hand", default=30),
        discount_rate_pct=_weighted_avg(rows, "discount_rate_pct", default=10),
        price_per_gram_usd=_weighted_avg(rows, "price_per_gram_usd", default=7),
        active_retailers=max(len({str(r.get('retailer_id', i)) for i, r in enumerate(rows)}), 1),
        license_violations=sum(int(r.get("license_violations", 0) or 0) for r in rows),
        product_mix={
            "flower_pct": round(pct(flower), 2),
            "vape_pct": round(pct(vape), 2),
            "edible_pct": round(pct(edible), 2),
            "concentrate_pct": round(pct(concentrate), 2),
            "other_pct": round(pct(other), 2),
        },
    )


def _weighted_avg(rows: list[dict[str, Any]], key: str, default: float) -> float:
    if not rows:
        return default
    values = [float(r.get(key, default) or default) for r in rows]
    return round(sum(values) / len(values), 2)
