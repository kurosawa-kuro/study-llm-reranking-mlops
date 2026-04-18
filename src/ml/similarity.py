from __future__ import annotations


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0

    size = min(len(a), len(b))
    return float(sum(a[i] * b[i] for i in range(size)))
