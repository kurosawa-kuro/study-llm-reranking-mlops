from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import redis

_REDIS_HOST = os.getenv("REDIS_HOST", "redis")
_REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
_SEARCH_CACHE_TTL = int(os.getenv("SEARCH_CACHE_TTL_SECONDS", "120"))

# 接続失敗時もアプリを落とさないよう遅延初期化する
_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis(
            host=_REDIS_HOST,
            port=_REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=1,
        )
    return _client


def _make_cache_key(params: dict[str, Any]) -> str:
    normalized = json.dumps(params, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"search_result:{digest}"


def get_cached_search(params: dict[str, Any]) -> dict | None:
    """キャッシュヒット時は dict を返す。ミスまたは Redis 障害時は None。"""
    try:
        raw = _get_client().get(_make_cache_key(params))
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


def set_cached_search(params: dict[str, Any], result: dict) -> None:
    """検索結果を TTL 付きでキャッシュする。Redis 障害時は無視。"""
    try:
        _get_client().setex(
            _make_cache_key(params),
            _SEARCH_CACHE_TTL,
            json.dumps(result, ensure_ascii=False),
        )
    except Exception:
        pass
