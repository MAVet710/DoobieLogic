from __future__ import annotations

import csv
from io import StringIO
from typing import Any


def load_csv_bytes(file_bytes: bytes) -> list[dict[str, str]] | None:
    try:
        text = file_bytes.decode("utf-8-sig")
        reader = csv.DictReader(StringIO(text))
        return [dict(row) for row in reader]
    except Exception:
        return None


def basic_cannabis_mapping(rows: list[dict[str, Any]]) -> dict[str, list[Any]]:
    if not rows:
        return {}

    columns = {str(c).strip().lower(): c for c in rows[0].keys()}
    mapping = {
        "product": ["product", "item", "name", "product name", "sku name"],
        "category": ["category", "type", "product type", "class"],
        "price": ["price", "unit_price", "unit price", "retail price"],
        "quantity": ["quantity", "qty", "units sold", "units_sold", "sold"],
        "revenue": ["revenue", "sales", "total", "gross sales", "net sales"],
        "inventory": ["inventory", "on hand", "on_hand", "available quantity"],
        "brand": ["brand", "vendor", "producer"],
    }

    normalized: dict[str, list[Any]] = {}
    for key, options in mapping.items():
        for opt in options:
            if opt in columns:
                source_col = columns[opt]
                normalized[key] = [row.get(source_col) for row in rows]
                break
    return normalized


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _value_counts(values: list[Any], limit: int = 5) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value if value not in {None, ""} else "Unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit])


def analyze_mapped_data(mapped: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    if "quantity" in mapped:
        qty = [_to_float(v) or 0.0 for v in mapped["quantity"]]
        avg_qty = (sum(qty) / len(qty)) if qty else 0.0
        result["avg_quantity"] = round(avg_qty, 2)
        result["low_velocity_count"] = sum(1 for v in qty if v < avg_qty)
        result["zero_quantity_count"] = sum(1 for v in qty if v <= 0)

    if "price" in mapped:
        prices = [p for p in (_to_float(v) for v in mapped["price"]) if p is not None]
        if prices:
            result["avg_price"] = round(sum(prices) / len(prices), 2)
            result["min_price"] = round(min(prices), 2)
            result["max_price"] = round(max(prices), 2)

    if "revenue" in mapped:
        revenue = [_to_float(v) or 0.0 for v in mapped["revenue"]]
        result["total_revenue"] = round(sum(revenue), 2)

    if "inventory" in mapped:
        inv = [_to_float(v) or 0.0 for v in mapped["inventory"]]
        avg_inv = (sum(inv) / len(inv)) if inv else 0.0
        result["inventory_units"] = round(sum(inv), 2)
        result["high_inventory_count"] = sum(1 for v in inv if v > avg_inv)

    if "category" in mapped:
        result["top_categories"] = _value_counts(list(mapped["category"]))

    if "brand" in mapped:
        result["top_brands"] = _value_counts(list(mapped["brand"]))

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
