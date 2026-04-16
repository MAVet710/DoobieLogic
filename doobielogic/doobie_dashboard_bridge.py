from __future__ import annotations

import json
from typing import Any

import httpx

from .copilot import DoobieCopilot


class DoobieProvider:
    provider_name: str = "doobie"

    def __init__(self, base_url: str | None = None, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/") if isinstance(base_url, str) and base_url.strip() else None
        self.timeout = timeout
        self._copilot = DoobieCopilot()

    def is_available(self) -> bool:
        if not self.base_url:
            return True
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(f"{self.base_url}/health")
                return resp.status_code < 500
        except Exception:
            return True

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> str:
        if self.base_url:
            remote = self._generate_remote(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=max_tokens)
            if remote:
                return remote
        if "Mode: main_copilot" in user_prompt:
            question = self._extract_question(user_prompt)
            if question:
                try:
                    return self._copilot.ask(question=question, persona="buyer").answer
                except Exception:
                    pass
        return self._structured_fallback(user_prompt=user_prompt, max_chars=max(500, max_tokens * 4))

    def _generate_remote(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str | None:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/generate",
                    json={"system_prompt": system_prompt, "user_prompt": user_prompt, "max_tokens": max_tokens},
                )
            if resp.status_code >= 400:
                return None
            payload = resp.json()
            if isinstance(payload, dict):
                text = payload.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
            if isinstance(payload, str) and payload.strip():
                return payload.strip()
        except Exception:
            return None
        return None

    @staticmethod
    def _extract_question(user_prompt: str) -> str:
        for line in (user_prompt or "").splitlines():
            if line.startswith("Question:"):
                return line.split(":", 1)[1].strip()
        return ""

    @staticmethod
    def _extract_context(user_prompt: str) -> dict[str, Any]:
        marker = "Context:\n"
        if marker not in user_prompt:
            return {}
        raw = user_prompt.split(marker, 1)[1].strip()
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def _structured_fallback(self, user_prompt: str, max_chars: int) -> str:
        mode = "support"
        first_line = (user_prompt or "").splitlines()[0:1]
        if first_line and first_line[0].startswith("Mode:"):
            mode = first_line[0].split(":", 1)[1].strip() or mode
        context = self._extract_context(user_prompt)
        if mode == "buyer_brief":
            return self._buyer_brief_text(context)[:max_chars]
        if mode == "inventory_check":
            return self._inventory_check_text(context)[:max_chars]
        if mode == "extraction_ops_brief":
            return self._extraction_ops_text(context)[:max_chars]
        return self._main_copilot_text(context, question=self._extract_question(user_prompt))[:max_chars]

    @staticmethod
    def _buyer_brief_text(context: dict[str, Any]) -> str:
        tracked = context.get("tracked_skus", 0)
        risk = context.get("at_risk_skus", 0)
        low_stock = context.get("low_stock_count", 0)
        overstock = context.get("overstock_count", 0)
        missing = ", ".join(context.get("context_used", {}).get("missing_fields", []))
        lines = [
            f"Executive summary: Tracking {tracked} SKUs with {risk} currently flagged as at risk.",
            f"Reorder now: Prioritize low-stock items first ({low_stock} flagged) using the dashboard's current reorder view.",
            f"Overstock/watchouts: {overstock} overstock or aging signals need slow-mover cleanup and promo review.",
            "Next 7-day actions: Confirm top risk SKUs, align vendor replenishment, and monitor category concentration shifts.",
        ]
        if missing:
            lines.append(f"Data limits: Missing context fields ({missing}), so recommendations are conservative.")
        return "\n".join(lines)

    @staticmethod
    def _inventory_check_text(context: dict[str, Any]) -> str:
        inventory_rows = len(context.get("filtered_inventory", []) or [])
        reorder_rows = len(context.get("reorder_rows", []) or [])
        oos_rows = len(context.get("oos_rows", []) or [])
        low_stock_rows = len(context.get("low_stock_rows", []) or [])
        threshold = context.get("doh_threshold")
        threshold_text = f" at DOH threshold {threshold}" if threshold is not None else ""
        lines = [
            f"What stands out: Reviewing {inventory_rows} filtered inventory rows{threshold_text}.",
            f"Obvious risks: {oos_rows} out-of-stock rows and {low_stock_rows} low-stock rows are immediate service risks.",
            f"Buyer-friendly recommendations: Work reorder queue first ({reorder_rows} rows), then trim slow/aging inventory by category.",
        ]
        if inventory_rows == 0:
            lines.append("Inventory context is limited, but low-stock review should be your first focus.")
        return "\n".join(lines)

    @staticmethod
    def _main_copilot_text(context: dict[str, Any], question: str) -> str:
        workspace = context.get("workspace", "general")
        section = context.get("section_name", "overview")
        row_counts = context.get("row_counts", {})
        question_text = question or "No question provided."
        return (
            f"Direct answer: {question_text}\n"
            f"Current view: Workspace '{workspace}' in section '{section}'.\n"
            f"State snapshot: row counts {row_counts}.\n"
            "Next steps: Use the dashboard section filters to validate the highest-risk rows, then execute the smallest high-impact action."
        )

    @staticmethod
    def _extraction_ops_text(context: dict[str, Any]) -> str:
        alerts = len(context.get("extraction_alerts", []) or [])
        runs = len(context.get("run_summary_rows", []) or [])
        at_risk = context.get("at_risk_batch_count", 0)
        aging = len(context.get("aging_lots", []) or [])
        low_stock = context.get("low_stock_lot_count", 0)
        lines = [
            f"Operational health summary: {runs} run rows reviewed with {alerts} active extraction alerts.",
            f"Top interventions: Focus next on {at_risk} at-risk batches and clear high-aging queues ({aging} lots).",
            "QA/COA watchouts: Prioritize lots with repeated alert patterns and any delayed release signals.",
            f"Throughput/inventory recommendations: Stabilize run handoffs and address low-stock material pressure ({low_stock} low-stock lots).",
        ]
        if runs == 0 and alerts == 0:
            lines.append("Extraction inventory data is limited, so projected output recommendations are conservative.")
        return "\n".join(lines)
