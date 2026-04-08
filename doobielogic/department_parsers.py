from __future__ import annotations

from typing import Any

from doobielogic.parser import basic_cannabis_mapping


BOOLEAN_TRUE = {"1", "true", "yes", "y", "t"}


def _num(value: Any) -> float | None:
    try:
        if value in {None, ""}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in BOOLEAN_TRUE


def _collect(rows: list[dict[str, Any]], key: str) -> list[Any]:
    return [row.get(key) for row in rows if key in row]


def parse_department_file(rows: list[dict[str, Any]], department: str) -> dict:
    dept = (department or "retail_ops").lower()
    if not rows:
        return {}

    if dept == "retail_ops" or dept == "buyer":
        return basic_cannabis_mapping(rows)

    parsed: dict[str, list[Any]] = {}
    headers = rows[0].keys()
    for h in headers:
        vals = _collect(rows, h)
        lower_h = h.strip().lower()
        if lower_h.endswith("_flag"):
            parsed[lower_h] = [_bool(v) for v in vals]
        elif any(token in lower_h for token in ["_pct", "_g", "_hours", "_minutes", "_days", "_rate", "_units", "_sqft", "_count", "variance"]):
            parsed[lower_h] = [_num(v) for v in vals]
        else:
            parsed[lower_h] = vals
    return parsed
