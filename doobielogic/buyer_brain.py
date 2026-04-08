from __future__ import annotations

from typing import Any


def _as_list(mapped_data: dict[str, Any], key: str) -> list[Any] | None:
    value = mapped_data.get(key)
    if value is None:
        return None
    return list(value)


def _to_num(values: list[Any] | None) -> list[float] | None:
    if values is None:
        return None
    nums: list[float] = []
    for value in values:
        try:
            nums.append(float(value))
        except (TypeError, ValueError):
            nums.append(0.0)
    return nums


def _counts(values: list[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        key = str(value if value not in {None, ""} else "Unknown")
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items(), key=lambda item: item[1], reverse=True))


def detect_low_velocity(mapped_data: dict) -> dict:
    quantity = _to_num(_as_list(mapped_data, "quantity"))
    revenue = _to_num(_as_list(mapped_data, "revenue"))
    products = [str(v) for v in (_as_list(mapped_data, "product") or [])]

    if quantity is None and revenue is None:
        return {"status": "skipped", "reason": "quantity/revenue missing"}

    movement = quantity or revenue or []
    avg = (sum(movement) / len(movement)) if movement else 0.0
    threshold = avg * 0.5
    low_idx = [i for i, value in enumerate(movement) if value <= threshold]

    return {
        "status": "ok",
        "average_movement": round(avg, 2),
        "low_velocity_count": len(low_idx),
        "low_velocity_products": [products[i] for i in low_idx[:8]] if products else [],
        "rule": "<= 50% of file average movement",
    }


def detect_markdown_candidates(mapped_data: dict) -> dict:
    quantity = _to_num(_as_list(mapped_data, "quantity"))
    inventory = _to_num(_as_list(mapped_data, "inventory"))
    products = [str(v) for v in (_as_list(mapped_data, "product") or [])]

    if quantity is None or inventory is None:
        return {"status": "skipped", "reason": "quantity/inventory missing"}

    idx: list[int] = []
    for i, (qty, inv) in enumerate(zip(quantity, inventory)):
        if inv > qty * 3 or (qty <= 0 and inv > 0):
            idx.append(i)

    return {
        "status": "ok",
        "candidate_count": len(idx),
        "candidates": [products[i] for i in idx[:8]] if products else [],
        "rule": "inventory > 3x quantity or zero-sales with inventory",
    }


def analyze_brand_concentration(mapped_data: dict) -> dict:
    brands = _as_list(mapped_data, "brand")
    if brands is None:
        return {"status": "skipped", "reason": "brand missing"}
    counts = _counts(brands)
    if not counts:
        return {"status": "skipped", "reason": "brand empty"}
    top_brand, top_count = next(iter(counts.items()))
    total = sum(counts.values())
    top_share = top_count / total if total else 0
    return {
        "status": "ok",
        "top_brand": top_brand,
        "top_brand_share": round(top_share, 3),
        "high_concentration": top_share >= 0.4,
        "top_brands": dict(list(counts.items())[:5]),
    }


def analyze_category_concentration(mapped_data: dict) -> dict:
    categories = _as_list(mapped_data, "category")
    if categories is None:
        return {"status": "skipped", "reason": "category missing"}
    counts = _counts(categories)
    if not counts:
        return {"status": "skipped", "reason": "category empty"}
    top_category, top_count = next(iter(counts.items()))
    total = sum(counts.values())
    top_share = top_count / total if total else 0
    return {
        "status": "ok",
        "top_category": top_category,
        "top_category_share": round(top_share, 3),
        "high_concentration": top_share >= 0.45,
        "top_categories": dict(list(counts.items())[:5]),
    }


def summarize_buyer_opportunities(mapped_data: dict) -> dict:
    low_velocity = detect_low_velocity(mapped_data)
    markdown = detect_markdown_candidates(mapped_data)
    brand = analyze_brand_concentration(mapped_data)
    category = analyze_category_concentration(mapped_data)

    prices = [v for v in (_to_num(_as_list(mapped_data, "price")) or []) if v > 0]
    quantity = _to_num(_as_list(mapped_data, "quantity"))
    inventory = _to_num(_as_list(mapped_data, "inventory"))

    price_bands: dict[str, Any] = {"status": "skipped", "reason": "price missing"}
    if prices:
        mix = {"value": 0, "core": 0, "premium": 0, "ultra": 0}
        for price in prices:
            if price <= 15:
                mix["value"] += 1
            elif price <= 30:
                mix["core"] += 1
            elif price <= 50:
                mix["premium"] += 1
            else:
                mix["ultra"] += 1
        price_bands = {"status": "ok", "avg_price": round(sum(prices) / len(prices), 2), "price_band_mix": mix}

    inventory_risk: dict[str, Any] = {"status": "skipped", "reason": "inventory/quantity missing"}
    open_to_buy: dict[str, Any] = {"status": "heuristic", "observation": "insufficient fields"}
    if quantity is not None and inventory is not None and quantity:
        heavy_rows = sum(1 for qty, inv in zip(quantity, inventory) if inv > qty * 4)
        inv_total = sum(inventory)
        qty_total = sum(quantity)
        inventory_risk = {
            "status": "ok",
            "heavy_inventory_rows": int(heavy_rows),
            "total_inventory_units": round(inv_total, 2),
            "total_quantity_units": round(qty_total, 2),
        }
        open_to_buy = {
            "status": "heuristic",
            "inventory_to_movement_ratio": round(inv_total / max(qty_total, 1), 2),
            "weeks_of_cover_proxy": round(inv_total / qty_total, 2) if qty_total > 0 else None,
            "observation": "Proxy uses file quantity as movement and is heuristic.",
        }

    return {
        "low_velocity": low_velocity,
        "markdown_candidates": markdown,
        "brand_concentration": brand,
        "category_concentration": category,
        "price_band_analysis": price_bands,
        "inventory_risk": inventory_risk,
        "open_to_buy_proxy": open_to_buy,
        "grounding": "Heuristic file-derived buyer brain",
        "confidence": "medium",
    }


def render_buyer_brain_summary(results: dict) -> str:
    if not results:
        return "Buyer brain unavailable: no mapped file data detected."

    lines = ["Buyer brain (heuristic file analysis):"]
    low = results.get("low_velocity", {})
    if low.get("status") == "ok":
        lines.append(f"- Low-velocity rows: {low['low_velocity_count']} ({low['rule']}).")

    markdown = results.get("markdown_candidates", {})
    if markdown.get("status") == "ok":
        lines.append(f"- Markdown candidates: {markdown['candidate_count']} based on inventory-to-movement pressure.")

    brand = results.get("brand_concentration", {})
    if brand.get("status") == "ok":
        lines.append(
            f"- Brand concentration: {brand['top_brand']} at {round(brand['top_brand_share'] * 100, 1)}% of rows."
        )

    category = results.get("category_concentration", {})
    if category.get("status") == "ok":
        lines.append(
            f"- Category concentration: {category['top_category']} at {round(category['top_category_share'] * 100, 1)}% of rows."
        )

    price = results.get("price_band_analysis", {})
    if price.get("status") == "ok":
        lines.append(f"- Price ladder mix: {price['price_band_mix']} (avg ${price['avg_price']}).")

    inv = results.get("inventory_risk", {})
    if inv.get("status") == "ok":
        lines.append(f"- Inventory risk rows: {inv['heavy_inventory_rows']} with heavy cover.")

    otb = results.get("open_to_buy_proxy", {})
    if otb:
        lines.append(f"- OTB proxy: {otb.get('observation', 'Heuristic proxy used.')}.")

    if len(lines) == 1:
        lines.append("- Not enough mapped fields to generate buyer-brain insights.")
    return "\n".join(lines)
