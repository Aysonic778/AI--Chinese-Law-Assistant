from __future__ import annotations

import re
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


CITATION_PATTERN = re.compile(r"[《\[]([^》\]]+)[》\]]\s*(第[一二三四五六七八九十百零〇\d]+条)?")


def _to_citation(chunk: RetrievedChunk) -> Citation:
    return Citation(
        law=chunk.law_name,
        article=chunk.article_number,
        chunk_id=chunk.chroma_id,
        excerpt=chunk.content[:500],
        version_date=chunk.version_date,
    )


def _gate_score(chunk: RetrievedChunk) -> float:
    """检索门槛使用向量相似度（0~1），Reranker 仅用于排序。"""
    return chunk.score


def evaluate_retrieval(chunks: list[RetrievedChunk]) -> GroundingDecision:
    if not chunks:
        return GroundingDecision(
            response_type="refusal",
            chunks=[],
            citations=[],
            refusal_reason="资料库为空，请先导入法律文件。",
            grounding_score=0.0,
        )

    best_score = max(_gate_score(chunk) for chunk in chunks)
    if best_score < settings.min_relevance_score:
        soft_chunks = chunks[: settings.soft_refusal_top_k]
        return GroundingDecision(
            response_type="soft_refusal",
            chunks=soft_chunks,
            citations=[_to_citation(chunk) for chunk in soft_chunks],
            refusal_reason="根据当前资料库，未找到与您问题足够相关的法律依据，无法给出结论。",
            grounding_score=best_score,
        )

    usable = [chunk for chunk in chunks if _gate_score(chunk) >= settings.min_relevance_score]
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


def build_extractive_answer(decision: GroundingDecision, question: str) -> str:
    lines = [
        "根据资料库检索结果，相关原文摘录如下（未经 AI 改写）：",
        "",
    ]
    for index, chunk in enumerate(decision.chunks[:5], start=1):
        lines.append(f"{index}. {chunk.citation_label}")
        lines.append(chunk.content)
        lines.append("")
    lines.append("以上摘录来自资料库，如需完整结论请结合专业人士意见。")
    return "\n".join(lines).strip()


def verify_citations(answer: str, decision: GroundingDecision) -> bool:
    if not settings.enable_citation_verify:
        return True

    available = {
        (citation.law, citation.article): True
        for citation in decision.citations
    }
    available_laws = {citation.law for citation in decision.citations}

    for match in CITATION_PATTERN.finditer(answer):
        law = match.group(1).strip()
        article = (match.group(2) or "").strip()
        if law not in available_laws:
            return False
        if article and (law, article) not in available and not any(
            key[0] == law and key[1] == article for key in available
        ):
            return False
    return True
