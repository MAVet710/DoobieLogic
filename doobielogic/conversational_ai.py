from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from doobielogic.actionable_response import format_actionable_fallback
from doobielogic.conversation_context import build_conversation_profile
from doobielogic.jurisdictions import compliance_context_text, get_jurisdiction_context
from doobielogic.module_curriculum import curriculum_prompt
from doobielogic.professional_domains import professional_domain_prompt
from doobielogic.retrieval import build_retrieval_context


DEFAULT_OPENAI_MODEL = "gpt-5.6"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
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
    specialist_prompt = professional_domain_prompt(mode) or curriculum_prompt(mode)
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
        "You are DoobieLogic, a conversational AI for licensed cannabis professionals. Give the exact, useful answer first. "
        "Use plain language, distinguish supplied facts from assumptions, and never invent operational "
        "measurements, laws, citations, effective dates, or license requirements. Treat the supplied rules-engine result, "
        "curated records, and official source URLs as the evidence boundary. An official regulator home page is not proof of "
        "an exact rule. A curated record title or summary proves only the facts explicitly written in that title or summary; "
        "never expand it into unstated mandated warnings, fields, thresholds, font sizes, QR-code rules, testing standards, "
        "deadlines, or other legal requirements. Describe unsupported controls as operational best practices, never as 'must' "
        "or 'required by law'. Only state an exact legal requirement when the application context marks rule_verified=true "
        "and supplies that exact fact, or when an allowed official-source search directly supports it. "
        "Before returning the answer, audit every sentence for legal-sounding language. When rule_verified is false, do not "
        "use 'required', 'mandated', 'must', 'shall', 'illegal', or 'prohibited' to describe a jurisdictional rule, and never "
        "make universal legal claims such as 'required in every state' or 'all jurisdictions require'. Instead label the item "
        "as an operational best practice and say the official jurisdiction-specific requirement still needs confirmation. "
        "The compliance boundary must agree with every earlier table cell, heading, and action; do not state an unverified "
        "mandate first and retract it later. If evidence is summary_only, it cannot support any exact mandate not written there. "
        "If the user requests "
        "jurisdiction-specific guidance and the jurisdiction or license type is missing, "
        "ask one natural follow-up while still giving a universal operational baseline. Never mention internal routing or modes.\n\n"
        "RESPONSE CONTRACT\n"
        "Write a concise professional answer in Markdown using these sections when useful:\n"
        "- Direct answer\n"
        "- What to do now (numbered, observable actions)\n"
        "- Evidence to verify (specific records, fields, or measurements)\n"
        "- Compliance boundary (what is verified, what is not, and what requires official confirmation)\n"
        "For control, investigation, audit, or checklist questions, give at least five concrete checks. "
        "Do not bury the actions behind a generic summary. Do not repeat the same point in multiple sections.\n\n"
        f"{specialist_prompt}"
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
        self.client = client
        self.provider = "rules"
        self.model: str | None = None
        self.fallback_reason: str | None = None

        if requested in {"rules", "deterministic", "off", "disabled"}:
            self.fallback_reason = "Conversational model disabled by configuration."
            return
        if requested not in {"auto", "openai", "groq"}:
            self.fallback_reason = f"Unsupported AI provider '{requested}'."
            return
        if self.client is not None:
            self.provider = requested if requested in {"openai", "groq"} else "openai"
            default_model = DEFAULT_GROQ_MODEL if self.provider == "groq" else DEFAULT_OPENAI_MODEL
            env_model = "DOOBIE_GROQ_MODEL" if self.provider == "groq" else "DOOBIE_OPENAI_MODEL"
            self.model = str(model or os.environ.get(env_model, default_model)).strip()
            return

        groq_key = str(api_key or os.environ.get("GROQ_API_KEY", "")).strip() if requested == "groq" else str(os.environ.get("GROQ_API_KEY", "")).strip()
        openai_key = str(api_key or os.environ.get("OPENAI_API_KEY", "")).strip() if requested == "openai" else str(os.environ.get("OPENAI_API_KEY", "")).strip()
        selected = requested
        if requested == "auto":
            selected = "groq" if groq_key else ("openai" if openai_key else "rules")
        configured_key = groq_key if selected == "groq" else openai_key
        if not configured_key:
            self.fallback_reason = "No conversational provider key is configured (GROQ_API_KEY or OPENAI_API_KEY)."
            return
        try:
            from openai import OpenAI

            if selected == "groq":
                self.client = OpenAI(
                    api_key=configured_key,
                    base_url="https://api.groq.com/openai/v1",
                    timeout=45.0,
                    max_retries=2,
                )
                self.provider = "groq"
                self.model = str(model or os.environ.get("DOOBIE_GROQ_MODEL", DEFAULT_GROQ_MODEL)).strip()
            else:
                self.client = OpenAI(api_key=configured_key, timeout=45.0, max_retries=2)
                self.provider = "openai"
                self.model = str(model or os.environ.get("DOOBIE_OPENAI_MODEL", DEFAULT_OPENAI_MODEL)).strip()
        except (ImportError, TypeError) as exc:
            self.fallback_reason = f"Conversational client unavailable: {exc}"

    @property
    def status(self) -> ConversationStatus:
        return ConversationStatus(
            provider=self.provider,
            model=self.model if self.provider in {"openai", "groq"} else None,
            enabled=self.provider in {"openai", "groq"} and self.client is not None,
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
        profile = build_conversation_profile(
            question,
            state=state,
            primary_mode=mode,
            history=history,
        )
        resolved_state = str(profile.get("jurisdiction") or "").strip() or None
        retrieval = build_retrieval_context(
            question,
            state=resolved_state,
            primary_mode=mode,
            secondary_modes=list(profile.get("secondary_domains") or []),
        )
        current_sources = [
            str(source)
            for source in (enhanced.get("sources") or [])
            if str(source).startswith("http")
        ]
        enhanced["sources"] = list(dict.fromkeys([*current_sources, *retrieval["source_urls"]]))
        enhanced["conversation_context"] = profile
        enhanced["retrieval"] = {
            "status": retrieval["status"],
            "verified_rule_available": retrieval["verified_rule_available"],
            "warning": retrieval["warning"],
        }
        if resolved_state and not enhanced.get("compliance_context"):
            enhanced["compliance_context"] = retrieval.get("jurisdiction")
        if not self.status.enabled:
            enhanced["ai"] = self.status.to_dict()
            return format_actionable_fallback(enhanced)

        model_context = {
            "conversation_profile": profile,
            "routed_module": mode,
            "retrieval_context": retrieval,
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
                    "rule_verified",
                    "rule_effective_date",
                    "rule_scope",
                    "needs_clarification",
                    "missing_context",
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
            instructions = build_conversation_instructions(mode, resolved_state)
            if self.provider == "groq":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": instructions}, *conversation],
                    temperature=0.2,
                    max_tokens=1_800,
                )
                choices = getattr(response, "choices", None) or []
                output_text = str(getattr(getattr(choices[0], "message", None), "content", "") or "").strip() if choices else ""
            else:
                request_options: dict[str, Any] = {
                    "model": self.model,
                    "instructions": instructions,
                    "input": conversation,
                    "max_output_tokens": 1_800,
                }
                if mode == "compliance" and not enhanced.get("rule_verified"):
                    domains = _official_domains(resolved_state)
                    if domains:
                        request_options.update(
                            {
                                "tools": [{"type": "web_search", "filters": {"allowed_domains": domains}}],
                                "tool_choice": "auto",
                                "include": ["web_search_call.action.sources"],
                            }
                        )
                response = self.client.responses.create(**request_options)
                output_text = str(getattr(response, "output_text", "") or "").strip()
            if output_text:
                enhanced["answer"] = output_text
                citations = _web_citation_sources(response) if self.provider == "openai" else []
                if citations:
                    enhanced["sources"] = list(dict.fromkeys([*(enhanced.get("sources") or []), *citations]))
                enhanced["ai"] = self.status.to_dict()
                enhanced["response_contract_version"] = "actionable-v1"
                return enhanced
            enhanced["ai"] = ConversationStatus(
                provider="rules",
                model=None,
                enabled=False,
                fallback_reason="The conversational model returned no text.",
            ).to_dict()
            return format_actionable_fallback(enhanced)
        except Exception as exc:
            enhanced["ai"] = ConversationStatus(
                provider="rules",
                model=None,
                enabled=False,
                fallback_reason=f"Conversational model request failed: {type(exc).__name__}",
            ).to_dict()
            return format_actionable_fallback(enhanced)

