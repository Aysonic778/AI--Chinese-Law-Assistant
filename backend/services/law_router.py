from __future__ import annotations

from backend.config import settings
from backend.services.embeddings import get_collection, get_embedding_function


class LawRouter:
    """第一阶段：根据法律摘要向量匹配，选出相关法律名称。"""

    def route(self, query: str, top_n: int | None = None) -> list[tuple[str, float]]:
        top_n = top_n or settings.law_router_top_n
        collection = get_collection()
        if collection.count() == 0:
            return []

        result = collection.query(
            query_texts=[query],
            n_results=min(collection.count(), 50),
            where={"chunk_type": "law_summary"},
            include=["documents", "metadatas", "distances"],
        )

        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        if not metadatas:
            return self._route_from_articles(query, top_n)

        scores_by_law: dict[str, float] = {}
        for metadata, distance in zip(metadatas, distances, strict=True):
            law_name = metadata.get("law_name", "")
            if not law_name:
                continue
            similarity = 1.0 - float(distance)
            scores_by_law[law_name] = max(scores_by_law.get(law_name, 0.0), similarity)

        ranked = sorted(scores_by_law.items(), key=lambda item: item[1], reverse=True)
        filtered = [(name, score) for name, score in ranked if score >= settings.min_law_router_score]
        return filtered[:top_n] if filtered else ranked[:top_n]

    def _route_from_articles(self, query: str, top_n: int) -> list[tuple[str, float]]:
        collection = get_collection()
        result = collection.query(
            query_texts=[query],
            n_results=min(collection.count(), 30),
            include=["metadatas", "distances"],
        )
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        scores_by_law: dict[str, float] = {}
        for metadata, distance in zip(metadatas, distances, strict=True):
            law_name = metadata.get("law_name", "")
            if not law_name:
                continue
            similarity = 1.0 - float(distance)
            scores_by_law[law_name] = max(scores_by_law.get(law_name, 0.0), similarity)
        return sorted(scores_by_law.items(), key=lambda item: item[1], reverse=True)[:top_n]


def build_law_summary(law_name: str, chunk_texts: list[str]) -> str:
    preview = "\n".join(text[:300] for text in chunk_texts[:10])
    return f"{law_name}\n{preview}"
