from __future__ import annotations

from doobielogic.parser import analyze_mapped_data, basic_cannabis_mapping, render_insight_summary


def test_basic_mapping_and_analysis_with_rows():
    rows = [
        {"Product": "A", "Category": "flower", "Brand": "X", "Price": "20", "Qty": "1", "Revenue": "20", "Inventory": "10"},
        {"Product": "B", "Category": "vapes", "Brand": "Y", "Price": "40", "Qty": "0", "Revenue": "0", "Inventory": "30"},
    ]
    mapped = basic_cannabis_mapping(rows)

    insights = analyze_mapped_data(mapped)

    assert insights["avg_price"] == 30.0
    assert insights["zero_quantity_count"] == 1
    assert "flower" in insights["top_categories"]


def test_render_insight_summary_empty():
    text = render_insight_summary({})
    assert "No structured insights" in text
