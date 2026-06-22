from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.models.schemas import ChunkResponse, DocumentResponse
from backend.services.ingestion import get_chunk_by_chroma_id, list_documents

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("", response_model=list[DocumentResponse])
async def get_library(session: AsyncSession = Depends(get_db)) -> list[DocumentResponse]:
    documents = await list_documents(session)
    return [
        DocumentResponse(
            id=document.id,
            law_name=document.law_name,
            version_date=document.version_date,
            source_filename=document.source_filename,
            chunk_count=document.chunk_count,
        )
        for document in documents
    ]


@router.get("/citations/{chunk_id}", response_model=ChunkResponse)
async def get_citation(chunk_id: str, session: AsyncSession = Depends(get_db)) -> ChunkResponse:
    chunk = await get_chunk_by_chroma_id(session, chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Citation not found")
    return ChunkResponse(
        law_name=chunk.law_name,
        article_number=chunk.article_number,
        chapter=chunk.chapter,
        content=chunk.content,
        version_date=chunk.version_date,
    )
