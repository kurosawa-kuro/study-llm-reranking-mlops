from __future__ import annotations

import os
from typing import Any

import httpx


class MeiliClient:
    def __init__(
        self,
        base_url: str | None = None,
        index_name: str = "properties",
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        raw_url = base_url or os.getenv("MEILI_HTTP_ADDR", "meilisearch:7700")
        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            self.base_url = raw_url.rstrip("/")
        else:
            self.base_url = f"http://{raw_url.strip('/')}"

        self.index_name = index_name
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
            response = client.request(method, url, json=payload)
            response.raise_for_status()
            if response.content:
                return response.json()
            return {}

    def search(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/indexes/{self.index_name}/search", payload)

    def create_index_if_missing(self, primary_key: str = "id") -> None:
        indexes = self._request("GET", "/indexes")
        existing = {item.get("uid") for item in indexes.get("results", [])}
        if self.index_name in existing:
            return
        self._request(
            "POST",
            "/indexes",
            {"uid": self.index_name, "primaryKey": primary_key},
        )

    def set_filterable_attributes(self, attributes: list[str]) -> None:
        self._request(
            "PUT",
            f"/indexes/{self.index_name}/settings/filterable-attributes",
            attributes,
        )

    def add_documents(self, documents: list[dict[str, Any]]) -> None:
        if not documents:
            return
        self._request("POST", f"/indexes/{self.index_name}/documents", documents)

    def delete_documents_by_ids(self, ids: list[int]) -> None:
        if not ids:
            return
        self._request("POST", f"/indexes/{self.index_name}/documents/delete-batch", ids)
