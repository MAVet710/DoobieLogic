from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .models import CannabisInput, CannabisOutput


@dataclass
class BuyerWorkspace:
    buyer_id: str
    latest_input: CannabisInput | None = None
    latest_output: CannabisOutput | None = None
    sales_rows: list[dict[str, Any]] = field(default_factory=list)
    last_synced_at: date | None = None


class BuyerWorkspaceStore:
    def __init__(self):
        self._workspaces: dict[str, BuyerWorkspace] = {}

    def get_or_create(self, buyer_id: str) -> BuyerWorkspace:
        if buyer_id not in self._workspaces:
            self._workspaces[buyer_id] = BuyerWorkspace(buyer_id=buyer_id)
        return self._workspaces[buyer_id]

    def list_buyers(self) -> list[str]:
        return sorted(self._workspaces.keys())
