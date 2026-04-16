from doobielogic.buyer_dashboard_adapter import (
    generate_buyer_brief,
    generate_extraction_ops_brief,
    generate_inventory_check,
)
from doobielogic.extraction_dashboard_support import (
    interpret_extraction_alerts,
    interpret_extraction_inventory,
    interpret_process_tracker,
    interpret_projected_output,
    interpret_run_log,
)
from doobielogic.response_intelligence import (
    generate_buyer_brief_response,
    generate_copilot_response,
    generate_extraction_ops_response,
    generate_inventory_check_response,
)
from doobielogic.response_templates import (
    FALLBACK_RESPONSES,
    determine_risk_tone,
    format_currency,
    format_number,
    format_percent,
)


def test_buyer_brief_generator_has_expected_sections():
    context = {
        "tracked_skus": 50,
        "total_revenue": 250000,
        "at_risk_skus": 9,
        "low_stock_count": 4,
        "reorder_candidates": [{"product_name": "Blue Dream 3.5g", "current_stock": 10, "days_on_hand": 4, "velocity": 20}],
        "overstock_count": 3,
        "overstock_rows": [{"product_name": "OG Cart", "inventory": 100, "days_on_hand": 55}],
        "category_rollups": [{"category": "Flower", "revenue": 120000, "risk_level": "high"}],
    }
    text = generate_buyer_brief_response(context)
    assert "## Executive Summary" in text
    assert "## Reorder Now" in text
    assert "## Overstock / Watchouts" in text
    assert "## Category Risk" in text
    assert "## Next 7-Day Actions" in text


def test_inventory_check_generator_has_expected_sections():
    context = {
        "total_skus": 4,
        "total_units": 400,
        "out_of_stock_count": 1,
        "low_stock_count": 2,
        "doh_threshold": 30,
        "rows": [{"product_name": "A", "days_on_hand": 45, "inventory": 100, "sales": 2, "category": "Flower"}],
        "reorder_risk_rows": [{"product_name": "B", "current_stock": 2, "velocity": 10, "projected_stockout_date": "2026-04-20", "days_on_hand": 2}],
    }
    text = generate_inventory_check_response(context)
    assert "## What Stands Out" in text
    assert "## Obvious Risks" in text
    assert "## Recommendations" in text


def test_main_copilot_generator_handles_empty_context():
    text = generate_copilot_response({}, "what should I reorder?")
    assert "Next step:" in text
    assert "What I'd recommend:" in text


def test_extraction_ops_generator_has_expected_sections():
    context = {
        "avg_yield": 58,
        "efficiency": 68,
        "total_output": 1200,
        "run_count": 8,
        "at_risk_batches": 2,
        "failed_batches": 1,
        "alerts": [{"severity": "critical", "alert_type": "equipment"}],
        "aging_lots": 2,
        "low_available_stock": 1,
    }
    text = generate_extraction_ops_response(context)
    assert "## Operational Health" in text
    assert "## Top Interventions" in text
    assert "## QA / COA Watchouts" in text
    assert "## Throughput & Inventory Recommendations" in text
    assert "## Shift Focus" in text


def test_generators_handle_empty_context_gracefully():
    assert isinstance(generate_buyer_brief_response({}), str)
    assert isinstance(generate_inventory_check_response({}), str)
    assert isinstance(generate_copilot_response({}, "status?"), str)
    assert isinstance(generate_extraction_ops_response({}), str)


def test_fallbacks_returned_when_data_missing_in_adapter():
    assert generate_buyer_brief({})["text"] == FALLBACK_RESPONSES["buyer_brief"]
    assert generate_inventory_check({})["text"] == FALLBACK_RESPONSES["inventory_check"]
    assert generate_extraction_ops_brief({})["text"] == FALLBACK_RESPONSES["extraction_ops"]


def test_determine_risk_tone_variants():
    assert determine_risk_tone({}) == "limited_data"
    assert determine_risk_tone({"tracked_skus": 100, "total_revenue": 10000, "at_risk_skus": 4}) == "stable"
    assert determine_risk_tone({"tracked_skus": 100, "total_revenue": 10000, "at_risk_skus": 20}) == "mixed"
    assert determine_risk_tone({"tracked_skus": 100, "total_revenue": 10000, "at_risk_skus": 20, "out_of_stock_count": 2}) == "urgent"


def test_format_helpers_handle_none_and_invalid_values():
    assert format_currency(None) == "N/A"
    assert format_currency("bad") == "N/A"
    assert format_number(None) == "N/A"
    assert format_number("bad") == "N/A"
    assert format_percent(None) == "N/A"
    assert format_percent("bad") == "N/A"


def test_extraction_interpreters_handle_missing_fields():
    assert "No extraction run log data" in interpret_run_log([])
    assert "No active extraction alerts" in interpret_extraction_alerts([])
    assert "No process tracker batches" in interpret_process_tracker([])
    assert "No extraction inventory snapshot" in interpret_extraction_inventory([])
    assert "not available" in interpret_projected_output({})
