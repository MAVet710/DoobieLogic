from __future__ import annotations

from doobielogic.buyer_brain import (
    analyze_brand_concentration,
    detect_low_velocity,
    detect_markdown_candidates,
    render_buyer_brain_summary,
    summarize_buyer_opportunities,
)


def _sample():
    return {
        "product": ["A", "B", "C", "D"],
        "brand": ["X", "X", "Y", "X"],
        "category": ["flower", "flower", "vapes", "edibles"],
        "price": [20, 45, 30, 10],
        "quantity": [10, 0, 2, 1],
        "inventory": [12, 40, 20, 9],
        "revenue": [200, 0, 60, 10],
    }


def test_buyer_brain_flags_and_summary():
    data = _sample()
    low = detect_low_velocity(data)
    markdown = detect_markdown_candidates(data)
    brand = analyze_brand_concentration(data)
    all_results = summarize_buyer_opportunities(data)
    summary = render_buyer_brain_summary(all_results)

    assert low["status"] == "ok"
    assert markdown["candidate_count"] >= 1
    assert brand["top_brand"] == "X"
    assert "Buyer brain" in summary


def test_buyer_brain_missing_fields_graceful():
    data = {"product": ["A", "B"]}
    results = summarize_buyer_opportunities(data)
    assert results["low_velocity"]["status"] == "skipped"
    assert results["markdown_candidates"]["status"] == "skipped"
