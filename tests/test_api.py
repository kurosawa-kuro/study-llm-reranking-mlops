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
            "src.api.routes.search.run_ranked_search",
            return_value=_FakeSearchResult(items=_FAKE_ITEMS),
        ),
        patch(
            "src.api.routes.search.safe_log_ranked_search",
            return_value=(42, 7),
        ),
    ):
        resp = client.get("/search", params={"q": "マンション", "city": "札幌市"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["search_log_id"] == 42
    assert body["compare_log_id"] == 7
    assert body["count"] == 2
    assert body["items"][0]["id"] == 1


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
