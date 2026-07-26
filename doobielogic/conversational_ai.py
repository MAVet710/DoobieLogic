from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from doobielogic.jurisdictions import compliance_context_text, get_jurisdiction_context
from doobielogic.module_curriculum import curriculum_prompt


DEFAULT_MODEL = "gpt-5.6"
MAX_HISTORY_MESSAGES = 12
MAX_CONTEXT_CHARACTERS = 30_000


@dataclass(frozen=True)
class ConversationStatus:
    provider: str
    model: str | None
    enabled: bool
    fallback_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "enabled": self.enabled,
            "fallback_reason": self.fallback_reason,
        }


def _clean_history(history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    for item in (history or [])[-MAX_HISTORY_MESSAGES:]:
        role = str(item.get("role") or "").strip().casefold()
        if role not in {"user", "assistant"}:
            continue
        content = item.get("content")
        if content is None and isinstance(item.get("result"), dict):
            content = item["result"].get("answer")
        text = str(content or "").strip()
        if text:
            cleaned.append({"role": role, "content": text[:4_000]})
    return cleaned


def _bounded_json(value: Any) -> str:
    try:
        text = json.dumps(value, default=str, ensure_ascii=True, separators=(",", ":"))
    except (TypeError, ValueError):
        text = json.dumps({"unavailable": True})
    if len(text) <= MAX_CONTEXT_CHARACTERS:
        return text
    return text[:MAX_CONTEXT_CHARACTERS] + "...[truncated]"


def _official_domains(state: str | None) -> list[str]:
    context = get_jurisdiction_context(state)
    domains: list[str] = []
    for source in context.sources if context else ():
        host = (urlparse(source.url).hostname or "").lower()
        if host and host not in domains:
            domains.append(host)
    return domains


def _web_citation_sources(response: Any) -> list[str]:
    sources: list[str] = []
    for item in getattr(response, "output", None) or []:
        for content in getattr(item, "content", None) or []:
            for annotation in getattr(content, "annotations", None) or []:
                url = str(getattr(annotation, "url", "") or "").strip()
                title = str(getattr(annotation, "title", "") or "").strip()
                rendered = f"{title}: {url}" if title else url
                if rendered and rendered not in sources:
                    sources.append(rendered)
    return sources


def build_conversation_instructions(mode: str, state: str | None = None) -> str:
    compliance_policy = ""
    if mode == "compliance":
        compliance_policy = (
            "\n\nCOMPLIANCE EVIDENCE POLICY\n"
            f"{compliance_context_text(state)}\n"
            "For a current jurisdiction-specific rule not already verified in the application context, "
            "use web search and rely only on the allowed official regulator or government domains. "
            "Never fill a missing current rule from model memory or a secondary source. State the "
            "effective date when available, link the controlling official authority, clearly distinguish "
            "purchase limits from possession limits, and require regulator or qualified-counsel "
            "verification before a licensee changes operations."
        )
    return (
        "You are DoobieLogic, a cannabis-business AI assistant. Give a direct, useful answer first. "
        "Use plain language, distinguish supplied facts from assumptions, and never invent operational "
        "measurements, laws, citations, or license requirements. Treat the supplied rules-engine result "
        "and source URLs as the evidence boundary. Ask for the minimum missing information when a "
        "responsible recommendation needs more evidence.\n\n"
        f"{curriculum_prompt(mode)}"
        f"{compliance_policy}"
    )


class ConversationService:
    """Optional conversational model layer with a deterministic rules-engine fallback."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ):
        requested = str(provider or os.environ.get("DOOBIE_AI_PROVIDER", "auto")).strip().casefold()
        self.model = str(model or os.environ.get("DOOBIE_OPENAI_MODEL", DEFAULT_MODEL)).strip()
        self.client = client
        self.provider = "rules"
        self.fallback_reason: str | None = None

        if requested in {"rules", "deterministic", "off", "disabled"}:
            self.fallback_reason = "Conversational model disabled by configuration."
            return
        if requested not in {"auto", "openai"}:
            self.fallback_reason = f"Unsupported AI provider '{requested}'."
            return
        if self.client is not None:
            self.provider = "openai"
            return

        configured_key = str(api_key or os.environ.get("OPENAI_API_KEY", "")).strip()
        if not configured_key:
            self.fallback_reason = "OPENAI_API_KEY is not configured."
            return
        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=configured_key, timeout=45.0, max_retries=2)
            self.provider = "openai"
        except (ImportError, TypeError) as exc:
            self.fallback_reason = f"OpenAI client unavailable: {exc}"

    @property
    def status(self) -> ConversationStatus:
        return ConversationStatus(
            provider=self.provider,
            model=self.model if self.provider == "openai" else None,
            enabled=self.provider == "openai" and self.client is not None,
            fallback_reason=self.fallback_reason,
        )

    def enhance(
        self,
        result: dict[str, Any],
        *,
        question: str,
        mode: str,
        state: str | None = None,
        data: dict[str, Any] | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        enhanced = dict(result)
        if not self.status.enabled:
            enhanced["ai"] = self.status.to_dict()
            return enhanced

        model_context = {
            "jurisdiction": state,
            "routed_module": mode,
            "rules_engine_result": {
                key: enhanced.get(key)
                for key in (
                    "answer",
                    "explanation",
                    "recommendations",
                    "risk_flags",
                    "inefficiencies",
                    "confidence",
                    "sources",
                    "compliance_context",
                )
            },
            "business_data": data or {},
        }
        conversation = _clean_history(history)
        conversation.append(
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    "Verified application context (JSON):\n"
                    f"{_bounded_json(model_context)}"
                ),
            }
        )
        try:
            request_options: dict[str, Any] = {
                "model": self.model,
                "instructions": build_conversation_instructions(mode, state),
                "input": conversation,
                "max_output_tokens": 1_800,
            }
            if mode == "compliance" and not enhanced.get("rule_verified"):
                domains = _official_domains(state)
                if domains:
                    request_options.update(
                        {
                            "tools": [
                                {
                                    "type": "web_search",
                                    "filters": {"allowed_domains": domains},
                                }
                            ],
                            "tool_choice": "auto",
                            "include": ["web_search_call.action.sources"],
                        }
                    )
            response = self.client.responses.create(
                **request_options
            )
            output_text = str(getattr(response, "output_text", "") or "").strip()
            if output_text:
                enhanced["answer"] = output_text
                citations = _web_citation_sources(response)
                if citations:
                    enhanced["sources"] = list(dict.fromkeys([*(enhanced.get("sources") or []), *citations]))
                enhanced["ai"] = self.status.to_dict()
                return enhanced
            enhanced["ai"] = ConversationStatus(
                provider="rules",
                model=None,
                enabled=False,
                fallback_reason="The conversational model returned no text.",
            ).to_dict()
            return enhanced
        except Exception as exc:
            enhanced["ai"] = ConversationStatus(
                provider="rules",
                model=None,
                enabled=False,
                fallback_reason=f"Conversational model request failed: {type(exc).__name__}",
            ).to_dict()
            return enhanced
