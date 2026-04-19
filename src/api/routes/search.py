from fastapi import APIRouter, HTTPException, Query
from httpx import HTTPError

from src.clients.redis_client import get_cached_search, set_cached_search
from src.core.logging import get_logger, RequestContextVar
from src.services.search.query_filter_builder import build_search_payload
from src.services.search.property_search_service import run_ranked_search, safe_log_ranked_search

logger = get_logger(__name__)
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
    request_id = RequestContextVar.get("request_id", "unknown")
    logger.info(
        "search_started",
        extra={
            "request_id": request_id,
            "user_id": user_id or "anonymous",
            "query": q,
            "city": city,
            "layout": layout,
            "limit": limit,
        },
    )

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
        logger.info(
            "search_completed_from_cache",
            extra={
                "request_id": request_id,
                "user_id": user_id or "anonymous",
                "result_count": cached.get("count", 0),
            },
        )
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
        logger.error(
            "search_backend_error",
            extra={
                "request_id": request_id,
                "user_id": user_id or "anonymous",
                "error": str(exc),
                "error_type": "HTTPError",
            },
        )
        raise HTTPException(status_code=502, detail="Search backend unavailable") from exc
    except TimeoutError as exc:
        logger.error(
            "search_timeout",
            extra={
                "request_id": request_id,
                "user_id": user_id or "anonymous",
                "error": str(exc),
            },
        )
        raise HTTPException(status_code=504, detail="Search request timed out") from exc
    except Exception as exc:
        logger.error(
            "search_unexpected_error",
            extra={
                "request_id": request_id,
                "user_id": user_id or "anonymous",
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Search failed") from exc

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
