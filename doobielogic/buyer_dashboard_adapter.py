"""Adapter layer wiring dashboard context sourcing to response intelligence generators."""

from __future__ import annotations

from doobielogic.dashboard_support import (
    source_buyer_brief_context,
    source_extraction_ops_context,
    source_inventory_check_context,
    source_main_copilot_context,
)
from doobielogic.response_intelligence import (
    generate_buyer_brief_response,
    generate_copilot_response as generate_copilot_text,
    generate_extraction_ops_response,
    generate_inventory_check_response,
)
from doobielogic.response_templates import FALLBACK_RESPONSES, determine_risk_tone


def _response_payload(mode: str, tone: str, text: str, context: dict, completeness: str) -> dict:
    """Return the shared response payload shape for all dashboard adapter outputs."""
    return {
        "text": text,
        "mode": mode,
        "provider": "doobie",
        "tone": tone,
        "context_used": {
            "current_section": context.get("current_section"),
            "row_count": context.get("row_count"),
            "tracked_skus": context.get("tracked_skus") or context.get("total_skus"),
            "has_revenue": context.get("total_revenue") is not None,
            "has_risk_data": context.get("at_risk_skus") is not None,
            "data_completeness": completeness,
        },
    }


def generate_buyer_brief(dashboard_context: dict) -> dict:
    """Generate a buyer brief response payload from raw dashboard context."""
    context = source_buyer_brief_context(dashboard_context)
    tone = determine_risk_tone(context)
    has_data = context.get("tracked_skus") is not None or context.get("total_revenue") is not None
    text = generate_buyer_brief_response(context) if has_data else FALLBACK_RESPONSES["buyer_brief"]
    return _response_payload("buyer_brief", tone, text, context, "full" if has_data else "limited")


def generate_inventory_check(dashboard_context: dict) -> dict:
    """Generate an inventory check response payload from raw dashboard context."""
    context = source_inventory_check_context(dashboard_context)
    tone = determine_risk_tone(context)
    has_data = context.get("total_skus") is not None or bool(context.get("rows"))
    text = generate_inventory_check_response(context) if has_data else FALLBACK_RESPONSES["inventory_check"]
    return _response_payload("inventory_check", tone, text, context, "full" if has_data else "limited")


def generate_copilot_answer(dashboard_context: dict, question: str) -> dict:
    """Generate a main copilot response payload for a section-aware user question."""
    context = source_main_copilot_context(dashboard_context)
    tone = determine_risk_tone(context)
    has_data = context.get("current_section") is not None or context.get("row_count") is not None
    text = generate_copilot_text(context, question) if has_data else FALLBACK_RESPONSES["main_copilot"]
    return _response_payload("main_copilot", tone, text, context, "full" if has_data else "limited")


def generate_extraction_ops_brief(dashboard_context: dict) -> dict:
    """Generate an extraction operations brief payload from raw dashboard context."""
    context = source_extraction_ops_context(dashboard_context)
    tone = determine_risk_tone(context)
    has_data = context.get("avg_yield") is not None or context.get("run_count") is not None or bool(context.get("alerts"))
    text = generate_extraction_ops_response(context) if has_data else FALLBACK_RESPONSES["extraction_ops"]
    return _response_payload("extraction_ops", tone, text, context, "full" if has_data else "limited")
