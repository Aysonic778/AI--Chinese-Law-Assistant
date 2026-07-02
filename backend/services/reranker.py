from __future__ import annotations

from functools import lru_cache

from sentence_transformers import CrossEncoder

from backend.config import settings


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    return CrossEncoder(settings.reranker_model, device=settings.embedding_device)


def rerank(query: str, passages: list[str], top_k: int | None = None) -> list[tuple[int, float]]:
    if not passages:
        return []

    top_k = top_k or settings.rerank_top_k
    model = get_reranker()
    pairs = [[query, passage] for passage in passages]
    scores = model.predict(pairs)
    ranked = sorted(enumerate(scores), key=lambda item: float(item[1]), reverse=True)
    return [(index, float(score)) for index, score in ranked[:top_k]]
