"""
正常系テスト: API エンドポイント（/health, /search, /feedback）
外部依存（DB / Meilisearch）はすべて unittest.mock でモック。
"""
from dataclasses import dataclass, field
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------
def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /search  — run_ranked_search / safe_log_ranked_search をモック
# ---------------------------------------------------------------------------
@dataclass
class _FakeSearchResult:
    items: list = field(default_factory=list)


_FAKE_ITEMS = [
    {"id": 1, "title": "物件A", "price": 80000, "me5_score": 0.9, "lgbm_score": 0.8},
    {"id": 2, "title": "物件B", "price": 70000, "me5_score": 0.7, "lgbm_score": 0.6},
]


def test_search_happy_path():
    with (
        patch(
            "src.api.routes.search.get_cached_search",
            return_value=None,
        ),
        patch(
            "src.api.routes.search.run_ranked_search",
            return_value=_FakeSearchResult(items=_FAKE_ITEMS),
        ),
        patch(
            "src.api.routes.search.safe_log_ranked_search",
            return_value=(42, 7),
        ),
        patch("src.api.routes.search.set_cached_search"),
    ):
        resp = client.get("/search", params={"q": "マンション", "city": "札幌市"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["search_log_id"] == 42
    assert body["compare_log_id"] == 7
    assert body["count"] == 2
    assert body["items"][0]["id"] == 1


def test_search_cache_hit():
    cached_response = {
        "search_log_id": 99,
        "compare_log_id": 5,
        "count": 1,
        "items": [{"id": 10, "title": "キャッシュ物件"}],
    }
    with patch(
        "src.api.routes.search.get_cached_search",
        return_value=cached_response,
    ):
        resp = client.get("/search", params={"q": "マンション"})

    assert resp.status_code == 200
    assert resp.json()["search_log_id"] == 99


# ---------------------------------------------------------------------------
# /feedback
# ---------------------------------------------------------------------------
def test_feedback_happy_path():
    with patch(
        "src.api.routes.feedback.apply_feedback",
        return_value=True,
    ):
        resp = client.post(
            "/feedback",
            json={
                "user_id": 1,
                "property_id": 5,
                "action": "favorite",
                "search_log_id": 42,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["property_id"] == 5
    assert body["action"] == "favorite"
    assert body["search_log_updated"] is True

# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------
def test_search_empty_query():
    """Test search with empty query string."""
    with (
        patch(
            "src.api.routes.search.get_cached_search",
            return_value=None,
        ),
        patch(
            "src.api.routes.search.run_ranked_search",
            return_value=_FakeSearchResult(items=[]),
        ),
        patch(
            "src.api.routes.search.safe_log_ranked_search",
            return_value=(None, None),
        ),
        patch("src.api.routes.search.set_cached_search"),
    ):
        resp = client.get("/search", params={"q": ""})

    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_search_query_too_long():
    """Test search with query exceeding max_length (500)."""
    long_query = "a" * 501
    resp = client.get("/search", params={"q": long_query})
    
    # Should fail validation with 422
    assert resp.status_code == 422


def test_search_invalid_limit():
    """Test search with invalid limit (should fail validation)."""
    resp = client.get("/search", params={"q": "test", "limit": 0})
    assert resp.status_code == 422

    resp = client.get("/search", params={"q": "test", "limit": 101})
    assert resp.status_code == 422


def test_search_invalid_candidate_limit():
    """Test search with invalid candidate_limit (should fail validation)."""
    resp = client.get("/search", params={"q": "test", "candidate_limit": 0})
    assert resp.status_code == 422

    resp = client.get("/search", params={"q": "test", "candidate_limit": 201})
    assert resp.status_code == 422


def test_search_meilisearch_unavailable():
    """Test search when Meilisearch is unavailable (ConnectionError)."""
    with patch(
        "src.api.routes.search.get_cached_search",
        return_value=None,
    ), patch(
        "src.api.routes.search.run_ranked_search",
        side_effect=ConnectionError("Connection refused"),
    ):
        resp = client.get("/search", params={"q": "test"})

    # Global exception handler should return 500 for generic ConnectionError
    assert resp.status_code == 500


def test_search_timeout():
    """Test search when request times out."""
    with patch(
        "src.api.routes.search.get_cached_search",
        return_value=None,
    ), patch(
        "src.api.routes.search.run_ranked_search",
        side_effect=TimeoutError("Request timed out"),
    ):
        resp = client.get("/search", params={"q": "test"})

    assert resp.status_code == 504


def test_feedback_invalid_action():
    """Test feedback with invalid action (should fail validation)."""
    resp = client.post(
        "/feedback",
        json={
            "user_id": 1,
            "property_id": 5,
            "action": "invalid_action",
            "search_log_id": 42,
        },
    )
    
    # Should fail validation with 422
    assert resp.status_code == 422


def test_feedback_invalid_property_id():
    """Test feedback with invalid property_id (should fail validation)."""
    resp = client.post(
        "/feedback",
        json={
            "user_id": 1,
            "property_id": 0,  # property_id must be > 0
            "action": "favorite",
            "search_log_id": 42,
        },
    )
    
    # Should fail validation with 422
    assert resp.status_code == 422


def test_feedback_invalid_search_log_id():
    """Test feedback with invalid search_log_id (should fail validation)."""
    resp = client.post(
        "/feedback",
        json={
            "user_id": 1,
            "property_id": 5,
            "action": "favorite",
            "search_log_id": 0,  # search_log_id must be > 0 or None
        },
    )
    
    # Should fail validation with 422
    assert resp.status_code == 422


def test_feedback_not_found():
    """Test feedback when search_log_id is not found in database."""
    with patch(
        "src.api.routes.feedback.apply_feedback",
        return_value=None,  # Simulate not found
    ):
        resp = client.post(
            "/feedback",
            json={
                "user_id": 1,
                "property_id": 5,
                "action": "favorite",
                "search_log_id": 99999,  # Non-existent ID
            },
        )

    # apply_feedback returns None for not found, API returns 404
    assert resp.status_code == 404


def test_feedback_server_error():
    """Test feedback when database error occurs."""
    with patch(
        "src.api.routes.feedback.apply_feedback",
        side_effect=Exception("Database connection failed"),
    ):
        resp = client.post(
            "/feedback",
            json={
                "user_id": 1,
                "property_id": 5,
                "action": "favorite",
                "search_log_id": 42,
            },
        )

    assert resp.status_code == 500