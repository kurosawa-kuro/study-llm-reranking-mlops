from fastapi import APIRouter, HTTPException, Query
from httpx import HTTPError

from src.infra.engagement import log_search_and_increment_impressions
from src.infra.me5_repository import fetch_property_embeddings
from src.infra.ranking_compare import log_ranking_comparison
from src.ml.me5_embed import encode_queries
from src.ranking.inference import rerank_with_lgbm
from src.ml.similarity import cosine_similarity
from src.search.meili_client import MeiliClient
from src.search.query_builder import build_search_payload

router = APIRouter()


def apply_me5_rerank(query: str, items: list[dict]) -> list[dict]:
    """ME5 スコアを各アイテムに付与する。ソートは LightGBM 再ランク後に一括して行う。"""
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

    # ソートは行わない（LightGBM が me5_score を特徴量として使い、最終ソートを担う）
    return items


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
    payload = build_search_payload(
        q=q,
        city=city,
        layout=layout,
        price_lte=price_lte,
        pet=pet,
        walk_min=walk_min,
        candidate_limit=candidate_limit,
    )

    client = MeiliClient(index_name="properties")

    try:
        result = client.search(payload)
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail="Search backend unavailable") from exc

    # candidate_limit 件を全件取得して再ランク対象とする（上位 limit 件への絞り込みは再ランク後）
    hits = result.get("hits", [])[:candidate_limit]
    meili_items = [
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

    meili_result_ids = [item["id"] for item in meili_items if item.get("id") is not None]

    items = list(meili_items)

    items = apply_me5_rerank(q, items)
    items = rerank_with_lgbm(items)

    # 再ランク済み候補から上位 limit 件を返却
    items = items[:limit]

    result_ids = [item["id"] for item in items if item.get("id") is not None]
    me5_scores = [float(item.get("me5_score", 0.0)) for item in items if item.get("id") is not None]

    # ログ・比較ログの失敗は検索結果返却に影響させない
    search_log_id: int | None = None
    compare_log_id: int | None = None
    try:
        search_log_id = log_search_and_increment_impressions(
            query=q,
            user_id=user_id,
            result_ids=result_ids,
            me5_scores=me5_scores,
        )
        compare_log_id = log_ranking_comparison(
            search_log_id=search_log_id,
            meili_result_ids=meili_result_ids,
            reranked_result_ids=result_ids,
        )
    except Exception:  # noqa: BLE001
        pass

    return {
        "search_log_id": search_log_id,
        "compare_log_id": compare_log_id,
        "count": len(items),
        "items": items,
    }
