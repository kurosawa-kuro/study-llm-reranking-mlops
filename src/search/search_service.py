from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.infra.repositories.engagement import log_search_and_increment_impressions
from src.infra.repositories.me5_repository import fetch_property_embeddings
from src.infra.repositories.ranking_compare import log_ranking_comparison
from src.ml.me5_embed import encode_queries
from src.ml.similarity import cosine_similarity
from src.ranking.inference import rerank_with_lgbm
from src.search.meili_client import MeiliClient


SearchItem = dict[str, Any]


@dataclass(slots=True)
class RankedSearchResult:
    items: list[SearchItem]
    meili_result_ids: list[int]
    result_ids: list[int]
    me5_scores: list[float]


def _build_search_items(hits: list[dict[str, Any]]) -> list[SearchItem]:
    return [
        {
            "id": hit.get("id"),
            "title": hit.get("title"),
            "city": hit.get("city"),
            "price": hit.get("price"),
            "layout": hit.get("layout"),
            "walk_min": hit.get("walk_min"),
            "pet": hit.get("pet"),
        }
        for hit in hits
    ]


def attach_me5_scores(query: str, items: list[SearchItem]) -> list[SearchItem]:
    if not items:
        return items

    if not query.strip():
        for item in items:
            item["me5_score"] = 0.0
        return items

    query_vector = encode_queries([query])[0]
    property_ids = [int(item["id"]) for item in items if item.get("id") is not None]
    embedding_map = fetch_property_embeddings(property_ids)

    for item in items:
        property_id = item.get("id")
        score = 0.0
        if property_id is not None:
            doc_vector = embedding_map.get(int(property_id))
            if doc_vector:
                score = cosine_similarity(query_vector, doc_vector)
        item["me5_score"] = float(round(score, 6))

    return items


def run_ranked_search(
    *,
    query: str,
    payload: dict[str, Any],
    limit: int,
    candidate_limit: int,
    index_name: str = "properties",
) -> RankedSearchResult:
    client = MeiliClient(index_name=index_name)
    result = client.search(payload)

    hits = result.get("hits", [])[:candidate_limit]
    meili_items = _build_search_items(hits)
    meili_result_ids = [int(item["id"]) for item in meili_items if item.get("id") is not None]

    reranked_items = rerank_with_lgbm(attach_me5_scores(query, list(meili_items)))[:limit]
    result_ids = [int(item["id"]) for item in reranked_items if item.get("id") is not None]
    me5_scores = [float(item.get("me5_score", 0.0)) for item in reranked_items if item.get("id") is not None]

    return RankedSearchResult(
        items=reranked_items,
        meili_result_ids=meili_result_ids,
        result_ids=result_ids,
        me5_scores=me5_scores,
    )


def safe_log_ranked_search(
    *,
    query: str,
    user_id: int | None,
    search_result: RankedSearchResult,
) -> tuple[int | None, int | None]:
    try:
        search_log_id = log_search_and_increment_impressions(
            query=query,
            user_id=user_id,
            result_ids=search_result.result_ids,
            me5_scores=search_result.me5_scores,
        )
        compare_log_id = log_ranking_comparison(
            search_log_id=search_log_id,
            meili_result_ids=search_result.meili_result_ids,
            reranked_result_ids=search_result.result_ids,
        )
        return search_log_id, compare_log_id
    except Exception:  # noqa: BLE001
        return None, None