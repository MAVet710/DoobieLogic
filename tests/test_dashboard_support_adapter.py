from __future__ import annotations

from doobielogic.buyer_dashboard_adapter import (
    generate_buyer_brief,
    generate_inventory_check,
    generate_main_copilot_response,
    generate_support_response,
)
from doobielogic.dashboard_support import source_buyer_brief_context
from doobielogic.doobie_dashboard_bridge import DoobieProvider


def test_source_buyer_brief_context_trims_rows():
    ctx = {
        "category_rows": [{"name": f"cat-{idx}"} for idx in range(20)],
        "risk_sku_rows": [{"sku": f"sku-{idx}"} for idx in range(40)],
    }
    out = source_buyer_brief_context(ctx)
    assert len(out["category_rows"]) == 8
    assert len(out["risk_sku_rows"]) == 20


def test_generate_support_response_modes_are_stable():
    context = {"filtered_inventory": [{"sku": "A"}], "doh_threshold": 21}
    res = generate_support_response(mode="inventory_dashboard", dashboard_context=context)
    assert res["provider"] == "doobie"
    assert res["mode"] == "inventory_check"
    assert isinstance(res["text"], str) and res["text"].strip()


def test_dashboard_adapter_functions_return_clean_payload():
    context = {"workspace": "buyer", "section_name": "inventory", "inventory_rows": [{"sku": "A"}]}
    for response in (
        generate_main_copilot_response("what matters now?", context),
        generate_buyer_brief(context),
        generate_inventory_check(context),
    ):
        assert set(response.keys()) == {"text", "mode", "provider", "context_used"}
        assert response["provider"] == "doobie"
        assert isinstance(response["text"], str) and response["text"].strip()


def test_doobie_provider_fallback_handles_missing_context():
    provider = DoobieProvider()
    text = provider.generate("system", "Mode: inventory_check\nContext:\n{}")
    assert "Inventory context is limited" in text
