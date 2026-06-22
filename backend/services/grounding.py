from __future__ import annotations

from dataclasses import dataclass

from backend.config import settings
from backend.services.ingestion import Citation
from backend.services.retriever import RetrievedChunk


@dataclass
class GroundingDecision:
    response_type: str
    chunks: list[RetrievedChunk]
    citations: list[Citation]
    refusal_reason: str | None = None
    grounding_score: float = 0.0


def _to_citation(chunk: RetrievedChunk) -> Citation:
    return Citation(
        law=chunk.law_name,
        article=chunk.article_number,
        chunk_id=chunk.chroma_id,
        excerpt=chunk.content[:500],
        version_date=chunk.version_date,
    )


def evaluate_retrieval(chunks: list[RetrievedChunk]) -> GroundingDecision:
    if not chunks:
        return GroundingDecision(
            response_type="refusal",
            chunks=[],
            citations=[],
            refusal_reason="资料库为空，请先导入法律文件。",
            grounding_score=0.0,
        )

    best_score = max(chunk.score for chunk in chunks)
    if best_score < settings.min_relevance_score:
        soft_chunks = chunks[: settings.soft_refusal_top_k]
        return GroundingDecision(
            response_type="soft_refusal",
            chunks=soft_chunks,
            citations=[_to_citation(chunk) for chunk in soft_chunks],
            refusal_reason="根据当前资料库，未找到与您问题足够相关的法律依据，无法给出结论。",
            grounding_score=best_score,
        )

    usable = [chunk for chunk in chunks if chunk.score >= settings.min_relevance_score]
    return GroundingDecision(
        response_type="answer",
        chunks=usable,
        citations=[_to_citation(chunk) for chunk in usable],
        grounding_score=best_score,
    )


def build_soft_refusal_message(decision: GroundingDecision) -> str:
    lines = [
        decision.refusal_reason or "资料库中未找到相关法律依据。",
        "",
        "以下是最接近的条文摘录（不足以得出结论，仅供参考）：",
    ]
    for index, citation in enumerate(decision.citations, start=1):
        label = f"{citation.law} {citation.article}".strip()
        lines.append(f"{index}. [{label}]")
        lines.append(citation.excerpt)
        lines.append("")
    lines.append("建议在「资料库管理」中补充相关法律文件后再次提问。")
    return "\n".join(lines).strip()
