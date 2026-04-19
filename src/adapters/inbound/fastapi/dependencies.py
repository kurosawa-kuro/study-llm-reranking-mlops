from __future__ import annotations

import os

import redis
from fastapi import Depends

from src.adapters.outbound.cache.redis_cache_adapter import RedisCacheAdapter
from src.adapters.outbound.embeddings.me5_embedding_adapter import ME5EmbeddingAdapter
from src.adapters.outbound.persistence.feedback_repository_adapter import (
    FeedbackRepositoryAdapter,
)
from src.adapters.outbound.persistence.ranking_compare_repository_adapter import (
    RankingCompareRepositoryAdapter,
)
from src.adapters.outbound.persistence.search_log_repository_adapter import (
    SearchLogRepositoryAdapter,
)
from src.adapters.outbound.ranking.lgbm_reranking_adapter import LightGBMRerankingAdapter
from src.adapters.outbound.search.meilisearch_property_search_adapter import (
    MeilisearchPropertySearchAdapter,
)
from src.application.usecases.record_feedback import RecordFeedbackUseCase
from src.application.usecases.search_properties import SearchPropertiesUseCase
from src.clients.meilisearch_client import MeiliClient
from src.ports.outbound.cache_port import CachePort
from src.ports.outbound.embedding_port import EmbeddingPort
from src.ports.outbound.feedback_port import FeedbackPort
from src.ports.outbound.property_search_port import PropertySearchPort
from src.ports.outbound.ranking_compare_log_port import RankingCompareLogPort
from src.ports.outbound.reranking_port import RerankingPort
from src.ports.outbound.search_log_port import SearchLogPort


def get_property_search_port() -> PropertySearchPort:
    client = MeiliClient(
        index_name=os.getenv("MEILI_INDEX", "properties"),
    )
    return MeilisearchPropertySearchAdapter(client=client)


def get_embedding_port() -> EmbeddingPort:
    return ME5EmbeddingAdapter()


def get_reranking_port() -> RerankingPort:
    return LightGBMRerankingAdapter()


def get_cache_port() -> CachePort:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
        socket_connect_timeout=1,
    )
    ttl = int(os.getenv("SEARCH_CACHE_TTL_SECONDS", "120"))
    return RedisCacheAdapter(client=redis_client, default_ttl_seconds=ttl)


def get_search_log_port() -> SearchLogPort:
    return SearchLogRepositoryAdapter()


def get_ranking_compare_log_port() -> RankingCompareLogPort:
    return RankingCompareRepositoryAdapter()


def get_feedback_port() -> FeedbackPort:
    return FeedbackRepositoryAdapter()


def get_search_properties_usecase(
    property_search_port: PropertySearchPort = Depends(get_property_search_port),
    embedding_port: EmbeddingPort = Depends(get_embedding_port),
    reranking_port: RerankingPort = Depends(get_reranking_port),
    cache_port: CachePort = Depends(get_cache_port),
    search_log_port: SearchLogPort = Depends(get_search_log_port),
    ranking_compare_log_port: RankingCompareLogPort = Depends(get_ranking_compare_log_port),
) -> SearchPropertiesUseCase:
    return SearchPropertiesUseCase(
        property_search_port=property_search_port,
        embedding_port=embedding_port,
        reranking_port=reranking_port,
        cache_port=cache_port,
        search_log_port=search_log_port,
        ranking_compare_log_port=ranking_compare_log_port,
        cache_ttl_seconds=int(os.getenv("SEARCH_CACHE_TTL_SECONDS", "120")),
    )


def get_record_feedback_usecase(
    feedback_port: FeedbackPort = Depends(get_feedback_port),
) -> RecordFeedbackUseCase:
    return RecordFeedbackUseCase(feedback_port=feedback_port)
