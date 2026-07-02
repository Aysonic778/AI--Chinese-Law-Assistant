from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import Conversation, Message
from backend.services.grounding import (
    GroundingDecision,
    build_extractive_answer,
    build_soft_refusal_message,
    evaluate_retrieval,
    verify_citations,
)
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
    conversation_id: int | None = None


class ChatService:
    def __init__(self) -> None:
        self.retriever = Retriever()

    async def chat(
        self,
        question: str,
        session: AsyncSession,
        conversation_id: int | None = None,
    ) -> ChatResult:
        conversation = await self._get_or_create_conversation(session, question, conversation_id)
        history = await self._load_history(session, conversation.id)
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
                conversation_id=conversation.id,
            )
            await self._save_message(session, conversation, question, result)
            return result

        content = await self._generate_answer(question, decision, history)
        if settings.enable_citation_verify and not verify_citations(content, decision):
            if settings.enable_extractive_fallback:
                content = build_extractive_answer(decision, question)
                result = ChatResult(
                    response_type="extractive",
                    content=content,
                    referenced_laws=sorted({citation.law for citation in decision.citations}),
                    citations=decision.citations,
                    grounding_score=decision.grounding_score,
                    conversation_id=conversation.id,
                )
                await self._save_message(session, conversation, question, result)
                return result
            content = build_extractive_answer(decision, question)

        result = ChatResult(
            response_type="answer",
            content=content,
            referenced_laws=sorted({citation.law for citation in decision.citations}),
            citations=decision.citations,
            grounding_score=decision.grounding_score,
            conversation_id=conversation.id,
        )
        await self._save_message(session, conversation, question, result)
        return result

    async def stream_chat(
        self,
        question: str,
        session: AsyncSession,
        conversation_id: int | None = None,
    ) -> AsyncIterator[str]:
        import json

        conversation = await self._get_or_create_conversation(session, question, conversation_id)
        history = await self._load_history(session, conversation.id)
        chunks = self.retriever.search(question)
        decision = evaluate_retrieval(chunks)

        meta = {
            "type": "meta",
            "response_type": decision.response_type,
            "referenced_laws": sorted({citation.law for citation in decision.citations}),
            "citations": [citation.to_dict() for citation in decision.citations],
            "grounding_score": decision.grounding_score,
            "refusal_reason": decision.refusal_reason,
            "conversation_id": conversation.id,
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
                conversation_id=conversation.id,
            )
            await self._save_message(session, conversation, question, result)
            yield 'data: {"type": "done"}\n\n'
            return

        full_content = ""
        async for token in self._stream_answer(question, decision, history):
            full_content += token
            yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"

        response_type = "answer"
        if settings.enable_citation_verify and not verify_citations(full_content, decision):
            if settings.enable_extractive_fallback:
                full_content = build_extractive_answer(decision, question)
                response_type = "extractive"

        result = ChatResult(
            response_type=response_type,
            content=full_content,
            referenced_laws=meta["referenced_laws"],
            citations=decision.citations,
            grounding_score=decision.grounding_score,
            conversation_id=conversation.id,
        )
        await self._save_message(session, conversation, question, result)
        yield 'data: {"type": "done"}\n\n'

    async def _get_or_create_conversation(
        self,
        session: AsyncSession,
        question: str,
        conversation_id: int | None,
    ) -> Conversation:
        if conversation_id:
            conversation = await session.get(Conversation, conversation_id)
            if conversation:
                return conversation
        title = question[:50] + ("..." if len(question) > 50 else "")
        conversation = Conversation(title=title)
        session.add(conversation)
        await session.flush()
        return conversation

    async def _load_history(self, session: AsyncSession, conversation_id: int) -> list[dict[str, str]]:
        result = await session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(settings.conversation_history_limit)
        )
        messages = list(reversed(list(result.all())))
        return [{"role": message.role, "content": message.content} for message in messages]

    def _build_user_prompt(self, question: str, decision: GroundingDecision, history: list[dict[str, str]]) -> str:
        context = build_context_block(decision.chunks)
        history_text = ""
        if history:
            lines = [f"{item['role']}: {item['content'][:300]}" for item in history[-4:]]
            history_text = "历史对话（仅供参考，回答仍须基于检索原文）：\n" + "\n".join(lines) + "\n\n"
        return f"{history_text}检索到的法律原文：\n{context}\n\n用户问题：{question}"

    async def _generate_answer(
        self,
        question: str,
        decision: GroundingDecision,
        history: list[dict[str, str]],
    ) -> str:
        client = get_llm_client()
        config = get_llm_config()
        response = await client.chat.completions.create(
            model=config.model,
            temperature=settings.llm_temperature,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_prompt(question, decision, history)},
            ],
        )
        return response.choices[0].message.content or ""

    async def _stream_answer(
        self,
        question: str,
        decision: GroundingDecision,
        history: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        client = get_llm_client()
        config = get_llm_config()
        stream = await client.chat.completions.create(
            model=config.model,
            temperature=settings.llm_temperature,
            stream=True,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_prompt(question, decision, history)},
            ],
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def _save_message(
        self,
        session: AsyncSession,
        conversation: Conversation,
        question: str,
        result: ChatResult,
    ) -> None:
        session.add(Message(conversation_id=conversation.id, role="user", content=question))
        session.add(
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content=result.content,
                response_type=result.response_type,
                citations_json=citations_to_json(result.citations),
            )
        )
        await session.commit()
