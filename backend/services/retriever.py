from __future__ import annotations

from dataclasses import dataclass

from backend.config import settings
from backend.services.law_router import LawRouter
from backend.services.reranker import rerank
from backend.services.embeddings import get_collection


@dataclass
class RetrievedChunk:
    chroma_id: str
    law_name: str
    article_number: str
    chapter: str
    content: str
    version_date: str
    score: float
    rerank_score: float = 0.0

    @property
    def citation_label(self) -> str:
        if self.article_number:
            return f"《{self.law_name}》{self.article_number}"
        return f"《{self.law_name}》"


class Retriever:
    def __init__(self) -> None:
        self.law_router = LawRouter()

    def search(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        top_k = top_k or settings.retrieval_top_k
        collection = get_collection()
        if collection.count() == 0:
            return []

        routed_laws = self.law_router.route(query)
        law_names = [name for name, _ in routed_laws]

        query_kwargs: dict = {
            "query_texts": [query],
            "n_results": min(top_k * 2, collection.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if law_names:
            query_kwargs["where"] = {
                "$and": [
                    {"chunk_type": {"$ne": "law_summary"}},
                    {"law_name": {"$in": law_names}},
                ]
            }
        else:
            query_kwargs["where"] = {"chunk_type": {"$ne": "law_summary"}}

        result = collection.query(**query_kwargs)

        chunks = self._parse_results(result)
        if not chunks and law_names:
            result = collection.query(
                query_texts=[query],
                n_results=min(top_k * 2, collection.count()),
                where={"chunk_type": {"$ne": "law_summary"}},
                include=["documents", "metadatas", "distances"],
            )
            chunks = self._parse_results(result)

        if not chunks:
            return []

        ranked_indices = rerank(query, [chunk.content for chunk in chunks], top_k=top_k)
        reranked: list[RetrievedChunk] = []
        for index, rerank_score in ranked_indices:
            chunk = chunks[index]
            reranked.append(
                RetrievedChunk(
                    chroma_id=chunk.chroma_id,
                    law_name=chunk.law_name,
                    article_number=chunk.article_number,
                    chapter=chunk.chapter,
                    content=chunk.content,
                    version_date=chunk.version_date,
                    score=chunk.score,
                    rerank_score=rerank_score,
                )
            )
        return reranked

    def _parse_results(self, result: dict) -> list[RetrievedChunk]:
        chunks: list[RetrievedChunk] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for chroma_id, document, metadata, distance in zip(ids, documents, metadatas, distances, strict=True):
            if metadata.get("chunk_type") == "law_summary":
                continue
            similarity = 1.0 - float(distance)
            chunks.append(
                RetrievedChunk(
                    chroma_id=chroma_id,
                    law_name=metadata.get("law_name", ""),
                    article_number=metadata.get("article_number", ""),
                    chapter=metadata.get("chapter", ""),
                    content=document,
                    version_date=metadata.get("version_date", ""),
                    score=similarity,
                )
            )
        return chunks
