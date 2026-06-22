from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.models.schemas import ChatRequest, ChatResponse, CitationResponse
from backend.services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])
chat_service = ChatService()


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, session: AsyncSession = Depends(get_db)) -> ChatResponse:
    try:
        result = await chat_service.chat(request.question, session)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ChatResponse(
        type=result.response_type,
        content=result.content,
        referenced_laws=result.referenced_laws,
        citations=[
            CitationResponse(
                law=citation.law,
                article=citation.article,
                chunk_id=citation.chunk_id,
                excerpt=citation.excerpt,
                version_date=citation.version_date,
            )
            for citation in result.citations
        ],
        grounding_score=result.grounding_score,
        refusal_reason=result.refusal_reason,
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest, session: AsyncSession = Depends(get_db)) -> StreamingResponse:
    try:
        generator = chat_service.stream_chat(request.question, session)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return StreamingResponse(generator, media_type="text/event-stream")
