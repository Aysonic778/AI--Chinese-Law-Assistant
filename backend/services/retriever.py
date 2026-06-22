from __future__ import annotations

from dataclasses import dataclass

from backend.config import settings
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

    @property
    def citation_label(self) -> str:
        if self.article_number:
            return f"《{self.law_name}》{self.article_number}"
        return f"《{self.law_name}》"


class Retriever:
    def search(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        top_k = top_k or settings.retrieval_top_k
        collection = get_collection()
        if collection.count() == 0:
            return []

        result = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        chunks: list[RetrievedChunk] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for chroma_id, document, metadata, distance in zip(ids, documents, metadatas, distances, strict=True):
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
