from __future__ import annotations

from .dashboard_support import (
    build_buyer_brief_prompt,
    build_extraction_ops_prompt,
    build_inventory_check_prompt,
    build_main_copilot_prompt,
    source_buyer_brief_context,
    source_extraction_ops_context,
    source_inventory_check_context,
    source_main_copilot_context,
)
from .doobie_dashboard_bridge import DoobieProvider

BUYER_SUPPORT_MODES = {
    "inventory_dashboard",
    "trends",
    "slow_movers",
    "po_builder",
    "buyer_intelligence",
}

EXTRACTION_SUPPORT_MODES = {
    "extraction_overview",
    "run_analytics",
    "process_tracker",
    "extraction_inventory",
    "toll_processing",
    "compliance_metrc",
    "extraction_data_input",
}


def _make_response(text: str, mode: str, context_used: dict) -> dict:
    clean_text = (text or "").strip() or "Context is limited, but start by reviewing the highest-risk rows in your current dashboard view."
    return {
        "text": clean_text,
        "mode": mode,
        "provider": "doobie",
        "context_used": context_used,
    }


def generate_main_copilot_response(question: str, dashboard_context: dict) -> dict:
    sourced = source_main_copilot_context(dashboard_context or {})
    system_prompt, user_prompt = build_main_copilot_prompt(sourced, user_question=question or "")
    provider = DoobieProvider()
    text = provider.generate(system_prompt=system_prompt, user_prompt=user_prompt)
    return _make_response(text=text, mode="main_copilot", context_used=sourced.get("context_used", {}))


def generate_buyer_brief(dashboard_context: dict) -> dict:
    sourced = source_buyer_brief_context(dashboard_context or {})
    system_prompt, user_prompt = build_buyer_brief_prompt(sourced)
    provider = DoobieProvider()
    text = provider.generate(system_prompt=system_prompt, user_prompt=user_prompt)
    return _make_response(text=text, mode="buyer_brief", context_used=sourced.get("context_used", {}))


def generate_inventory_check(dashboard_context: dict) -> dict:
    sourced = source_inventory_check_context(dashboard_context or {})
    system_prompt, user_prompt = build_inventory_check_prompt(sourced)
    provider = DoobieProvider()
    text = provider.generate(system_prompt=system_prompt, user_prompt=user_prompt)
    return _make_response(text=text, mode="inventory_check", context_used=sourced.get("context_used", {}))


def generate_extraction_ops_brief(dashboard_context: dict) -> dict:
    sourced = source_extraction_ops_context(dashboard_context or {})
    system_prompt, user_prompt = build_extraction_ops_prompt(sourced)
    provider = DoobieProvider()
    text = provider.generate(system_prompt=system_prompt, user_prompt=user_prompt)
    return _make_response(text=text, mode="extraction_ops_brief", context_used=sourced.get("context_used", {}))


def generate_support_response(mode: str, dashboard_context: dict, question: str = "") -> dict:
    safe_mode = (mode or "").strip().lower()
    if safe_mode == "main_copilot":
        return generate_main_copilot_response(question=question, dashboard_context=dashboard_context or {})
    if safe_mode in BUYER_SUPPORT_MODES:
        if safe_mode == "inventory_dashboard":
            return generate_inventory_check(dashboard_context or {})
        return generate_buyer_brief(dashboard_context or {})
    if safe_mode in EXTRACTION_SUPPORT_MODES:
        return generate_extraction_ops_brief(dashboard_context or {})
    return _make_response(
        text="Support mode not recognized. Using main copilot interpretation with available context.",
        mode=safe_mode or "unknown",
        context_used={},
    )
