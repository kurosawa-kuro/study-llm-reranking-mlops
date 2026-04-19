from __future__ import annotations

from typing import Any, Protocol

from src.application.dtos.search_dto import SearchQueryDTO

SearchQuery = SearchQueryDTO


class SearchUseCase(Protocol):
    def execute(self, query: SearchQuery) -> dict[str, Any]:
        ...
