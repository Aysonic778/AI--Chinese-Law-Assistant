import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import Conversation, Message
from backend.models.schemas import (
    ChatRequest,
    ChatResponse,
    CitationResponse,
    ConversationDetail,
    ConversationSummary,
    MessageResponse,
)
from backend.services.chat_service import ChatService
from backend.services.ingestion import Citation

router = APIRouter(prefix="/api/chat", tags=["chat"])
chat_service = ChatService()


def _citation_responses(citations: list[Citation]) -> list[CitationResponse]:
    return [
        CitationResponse(
            law=citation.law,
            article=citation.article,
            chunk_id=citation.chunk_id,
            excerpt=citation.excerpt,
            version_date=citation.version_date,
        )
        for citation in citations
    ]


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, session: AsyncSession = Depends(get_db)) -> ChatResponse:
    try:
        result = await chat_service.chat(request.question, session, request.conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ChatResponse(
        type=result.response_type,
        content=result.content,
        referenced_laws=result.referenced_laws,
        citations=_citation_responses(result.citations),
        grounding_score=result.grounding_score,
        refusal_reason=result.refusal_reason,
        conversation_id=result.conversation_id,
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest, session: AsyncSession = Depends(get_db)) -> StreamingResponse:
    try:
        generator = chat_service.stream_chat(request.question, session, request.conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return StreamingResponse(generator, media_type="text/event-stream")


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(session: AsyncSession = Depends(get_db)) -> list[ConversationSummary]:
    rows = await session.execute(
        select(
            Conversation.id,
            Conversation.title,
            Conversation.updated_at,
            func.count(Message.id).label("message_count"),
        )
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    )
    return [
        ConversationSummary(
            id=row.id,
            title=row.title,
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
            message_count=row.message_count or 0,
        )
        for row in rows.all()
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: int,
    session: AsyncSession = Depends(get_db),
) -> ConversationDetail:
    conversation = await session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    messages = await session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    message_list = []
    for message in messages.all():
        citations_raw = json.loads(message.citations_json or "[]")
        message_list.append(
            MessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                response_type=message.response_type,
                citations=[CitationResponse(**item) for item in citations_raw],
                created_at=message.created_at.isoformat() if message.created_at else "",
            )
        )

    return ConversationDetail(id=conversation.id, title=conversation.title, messages=message_list)
