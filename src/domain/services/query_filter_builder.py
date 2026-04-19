from __future__ import annotations

from typing import Any

from src.services.search.query_filter_builder import build_search_payload as _build_search_payload


def build_search_payload(
    q: str,
    city: str | None,
    layout: str | None,
    price_lte: int | None,
    pet: bool | None,
    walk_min: int | None,
    candidate_limit: int = 100,
) -> dict[str, Any]:
    """Domain service facade for search filter construction."""
    return _build_search_payload(
        q=q,
        city=city,
        layout=layout,
        price_lte=price_lte,
        pet=pet,
        walk_min=walk_min,
        candidate_limit=candidate_limit,
    )
