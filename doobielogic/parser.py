from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd


def load_csv_bytes(file_bytes: bytes) -> pd.DataFrame | None:
    try:
        return pd.read_csv(BytesIO(file_bytes))
    except Exception:
        return None


def basic_cannabis_mapping(df: pd.DataFrame) -> dict[str, pd.Series]:
    columns = {str(c).strip().lower(): c for c in df.columns}
    mapping = {
        "product": ["product", "item", "name", "product name", "sku name"],
        "category": ["category", "type", "product type", "class"],
        "price": ["price", "unit_price", "unit price", "retail price"],
        "quantity": ["quantity", "qty", "units sold", "units_sold", "sold"],
        "revenue": ["revenue", "sales", "total", "gross sales", "net sales"],
        "inventory": ["inventory", "on hand", "on_hand", "available quantity"],
        "brand": ["brand", "vendor", "producer"],
    }

    normalized: dict[str, pd.Series] = {}
    for key, options in mapping.items():
        for opt in options:
            if opt in columns:
                normalized[key] = df[columns[opt]]
                break
    return normalized


def analyze_mapped_data(mapped: dict[str, pd.Series]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    if "quantity" in mapped:
        qty = pd.to_numeric(mapped["quantity"], errors="coerce").fillna(0)
        result["avg_quantity"] = round(float(qty.mean()), 2)
        result["low_velocity_count"] = int((qty < qty.mean()).sum())
        result["zero_quantity_count"] = int((qty <= 0).sum())

    if "price" in mapped:
        price = pd.to_numeric(mapped["price"], errors="coerce").dropna()
        if not price.empty:
            result["avg_price"] = round(float(price.mean()), 2)
            result["min_price"] = round(float(price.min()), 2)
            result["max_price"] = round(float(price.max()), 2)

    if "revenue" in mapped:
        revenue = pd.to_numeric(mapped["revenue"], errors="coerce").fillna(0)
        result["total_revenue"] = round(float(revenue.sum()), 2)

    if "inventory" in mapped:
        inv = pd.to_numeric(mapped["inventory"], errors="coerce").fillna(0)
        result["inventory_units"] = round(float(inv.sum()), 2)
        result["high_inventory_count"] = int((inv > inv.mean()).sum()) if len(inv) else 0

    if "category" in mapped:
        cat = mapped["category"].astype(str).fillna("Unknown")
        result["top_categories"] = cat.value_counts().head(5).to_dict()

    if "brand" in mapped:
        brand = mapped["brand"].astype(str).fillna("Unknown")
        result["top_brands"] = brand.value_counts().head(5).to_dict()

    return result


def render_insight_summary(insights: dict[str, Any]) -> str:
    if not insights:
        return "No structured insights could be extracted from the uploaded file."

    lines: list[str] = []
    if "total_revenue" in insights:
        lines.append(f"- Total revenue in file: ${insights['total_revenue']}")
    if "avg_price" in insights:
        lines.append(f"- Average listed price: ${insights['avg_price']}")
    if "low_velocity_count" in insights:
        lines.append(f"- Potential low-velocity rows: {insights['low_velocity_count']}")
    if "zero_quantity_count" in insights:
        lines.append(f"- Zero or negative quantity rows: {insights['zero_quantity_count']}")
    if "inventory_units" in insights:
        lines.append(f"- Total inventory units represented: {insights['inventory_units']}")
    if "top_categories" in insights:
        lines.append(f"- Top categories: {insights['top_categories']}")
    if "top_brands" in insights:
        lines.append(f"- Top brands/vendors: {insights['top_brands']}")
    return "\n".join(lines)
