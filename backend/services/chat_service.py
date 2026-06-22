from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import Message
from backend.services.grounding import GroundingDecision, build_soft_refusal_message, evaluate_retrieval
from backend.services.ingestion import Citation, citations_to_json
from backend.services.llm import SYSTEM_PROMPT, build_context_block, get_llm_client, get_llm_config
from backend.services.retriever import Retriever


@dataclass
class ChatResult:
    response_type: str
    content: str
    referenced_laws: list[str]
    citations: list[Citation]
    grounding_score: float
    refusal_reason: str | None = None


class ChatService:
    def __init__(self) -> None:
        self.retriever = Retriever()

    async def chat(self, question: str, session: AsyncSession) -> ChatResult:
        chunks = self.retriever.search(question)
        decision = evaluate_retrieval(chunks)

        if decision.response_type in {"refusal", "soft_refusal"}:
            content = (
                decision.refusal_reason
                if decision.response_type == "refusal"
                else build_soft_refusal_message(decision)
            )
            result = ChatResult(
                response_type=decision.response_type,
                content=content,
                referenced_laws=sorted({citation.law for citation in decision.citations}),
                citations=decision.citations,
                grounding_score=decision.grounding_score,
                refusal_reason=decision.refusal_reason,
            )
            await self._save_message(session, question, result)
            return result

        content = await self._generate_answer(question, decision)
        result = ChatResult(
            response_type="answer",
            content=content,
            referenced_laws=sorted({citation.law for citation in decision.citations}),
            citations=decision.citations,
            grounding_score=decision.grounding_score,
        )
        await self._save_message(session, question, result)
        return result

    async def stream_chat(self, question: str, session: AsyncSession) -> AsyncIterator[str]:
        chunks = self.retriever.search(question)
        decision = evaluate_retrieval(chunks)

        meta = {
            "type": "meta",
            "response_type": decision.response_type,
            "referenced_laws": sorted({citation.law for citation in decision.citations}),
            "citations": [citation.to_dict() for citation in decision.citations],
            "grounding_score": decision.grounding_score,
            "refusal_reason": decision.refusal_reason,
        }
        yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

        if decision.response_type in {"refusal", "soft_refusal"}:
            content = (
                decision.refusal_reason
                if decision.response_type == "refusal"
                else build_soft_refusal_message(decision)
            )
            yield f"data: {json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"
            result = ChatResult(
                response_type=decision.response_type,
                content=content,
                referenced_laws=meta["referenced_laws"],
                citations=decision.citations,
                grounding_score=decision.grounding_score,
                refusal_reason=decision.refusal_reason,
            )
            await self._save_message(session, question, result)
            yield 'data: {"type": "done"}\n\n'
            return

        full_content = ""
        async for token in self._stream_answer(question, decision):
            full_content += token
            yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"

        result = ChatResult(
            response_type="answer",
            content=full_content,
            referenced_laws=meta["referenced_laws"],
            citations=decision.citations,
            grounding_score=decision.grounding_score,
        )
        await self._save_message(session, question, result)
        yield 'data: {"type": "done"}\n\n'

    async def _generate_answer(self, question: str, decision: GroundingDecision) -> str:
        client = get_llm_client()
        config = get_llm_config()
        context = build_context_block(decision.chunks)
        response = await client.chat.completions.create(
            model=config.model,
            temperature=settings.llm_temperature,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"检索到的法律原文：\n{context}\n\n用户问题：{question}",
                },
            ],
        )
        return response.choices[0].message.content or ""

    async def _stream_answer(self, question: str, decision: GroundingDecision) -> AsyncIterator[str]:
        client = get_llm_client()
        config = get_llm_config()
        context = build_context_block(decision.chunks)
        stream = await client.chat.completions.create(
            model=config.model,
            temperature=settings.llm_temperature,
            stream=True,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"检索到的法律原文：\n{context}\n\n用户问题：{question}",
                },
            ],
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def _save_message(self, session: AsyncSession, question: str, result: ChatResult) -> None:
        session.add(Message(role="user", content=question))
        session.add(
            Message(
                role="assistant",
                content=result.content,
                response_type=result.response_type,
                citations_json=citations_to_json(result.citations),
            )
        )
        await session.commit()
