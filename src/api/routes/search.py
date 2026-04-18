from fastapi import APIRouter, HTTPException, Query
from httpx import HTTPError

from src.clients.redis_client import get_cached_search, set_cached_search
from src.services.search.query_filter_builder import build_search_payload
from src.services.search.property_search_service import run_ranked_search, safe_log_ranked_search

router = APIRouter()


@router.get("/search")
def search(
    q: str = Query(default=""),
    user_id: int | None = Query(default=None),
    city: str | None = Query(default=None),
    layout: str | None = Query(default=None),
    price_lte: int | None = Query(default=None, ge=0),
    pet: bool | None = Query(default=None),
    walk_min: int | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    candidate_limit: int = Query(default=100, ge=1, le=200),
) -> dict:
    cache_params = {
        "q": q,
        "city": city,
        "layout": layout,
        "price_lte": price_lte,
        "pet": pet,
        "walk_min": walk_min,
        "limit": limit,
        "candidate_limit": candidate_limit,
    }

    cached = get_cached_search(cache_params)
    if cached is not None:
        return cached

    payload = build_search_payload(
        q=q,
        city=city,
        layout=layout,
        price_lte=price_lte,
        pet=pet,
        walk_min=walk_min,
        candidate_limit=candidate_limit,
    )

    try:
        search_result = run_ranked_search(
            query=q,
            payload=payload,
            limit=limit,
            candidate_limit=candidate_limit,
        )
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail="Search backend unavailable") from exc

    search_log_id, compare_log_id = safe_log_ranked_search(
        query=q,
        user_id=user_id,
        search_result=search_result,
    )

    response = {
        "search_log_id": search_log_id,
        "compare_log_id": compare_log_id,
        "count": len(search_result.items),
        "items": search_result.items,
    }

    set_cached_search(cache_params, response)

    return response
