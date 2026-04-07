from __future__ import annotations

import os
from typing import Any

import httpx


class CannabisSalesAPIClient:
    """Simple client for integrating external cannabis sales data APIs."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or os.getenv("DOOBIE_SALES_API_BASE_URL", "https://api.example.com")).rstrip("/")
        self.api_key = api_key or os.getenv("DOOBIE_SALES_API_KEY")
        self.timeout = timeout or float(os.getenv("DOOBIE_HTTP_TIMEOUT", "20"))

    def fetch_sales(self, state: str, start_date: str, end_date: str, page_size: int = 500) -> list[dict[str, Any]]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        rows: list[dict[str, Any]] = []
        page = 1

        with httpx.Client(timeout=self.timeout, headers=headers) as client:
            while True:
                resp = client.get(
                    f"{self.base_url}/sales",
                    params={
                        "state": state,
                        "start_date": start_date,
                        "end_date": end_date,
                        "page": page,
                        "page_size": page_size,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                batch = data.get("results", [])
                rows.extend(batch)

                if not data.get("next_page") or not batch:
                    break
                page += 1

        return rows
