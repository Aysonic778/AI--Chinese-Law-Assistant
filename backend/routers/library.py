from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.database import get_db
from backend.models.schemas import ChunkResponse, DocumentResponse
from backend.services.ingestion import (
    delete_document,
    get_chunk_by_chroma_id,
    import_law_text,
    list_documents,
)
from backend.services.parser import extract_text

router = APIRouter(prefix="/api/library", tags=["library"])

ALLOWED_SUFFIXES = {".txt", ".md", ".pdf", ".docx"}


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


@router.post("/documents", response_model=DocumentResponse)
async def upload_document(
    law_name: str = Form(...),
    version_date: str = Form(""),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    if not law_name.strip():
        raise HTTPException(status_code=400, detail="法律名称不能为空")

    filename = file.filename or "upload.txt"
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ".txt"
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持 .txt / .md / .pdf / .docx 文件")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 20MB")

    try:
        text = extract_text(Path(settings.upload_dir) / filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {exc}") from exc

    if not text.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")

    document = await import_law_text(
        session,
        text=text,
        law_name=law_name.strip(),
        version_date=version_date.strip(),
        source_filename=filename,
    )
    return DocumentResponse(
        id=document.id,
        law_name=document.law_name,
        version_date=document.version_date,
        source_filename=document.source_filename,
        chunk_count=document.chunk_count,
    )


@router.delete("/documents/{document_id}")
async def remove_document(document_id: int, session: AsyncSession = Depends(get_db)) -> dict[str, str]:
    try:
        await delete_document(session, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted"}


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
