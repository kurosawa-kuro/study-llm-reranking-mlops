from __future__ import annotations

from src.services.embeddings.similarity_service import cosine_similarity as _cosine_similarity


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Domain service facade for vector similarity."""
    return _cosine_similarity(vec_a, vec_b)
