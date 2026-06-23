from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import Chunk, Document
from backend.services.chunker import split_law_text
from backend.services.embeddings import get_collection, make_chroma_id


@dataclass
class Citation:
    law: str
    article: str
    chunk_id: str
    excerpt: str
    version_date: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


async def import_law_file(
    session: AsyncSession,
    file_path: Path,
    law_name: str,
    version_date: str,
    raw_text: str | None = None,
) -> Document:
    text = raw_text if raw_text is not None else file_path.read_text(encoding="utf-8")
    return await import_law_text(session, text, law_name, version_date, file_path.name)


async def import_law_text(
    session: AsyncSession,
    text: str,
    law_name: str,
    version_date: str,
    source_filename: str = "upload.txt",
) -> Document:
    chunks = split_law_text(text, law_name=law_name, version_date=version_date)

    existing = await session.scalar(select(Document).where(Document.law_name == law_name))
    if existing:
        for chunk in list(existing.chunks):
            get_collection().delete(ids=[chunk.chroma_id])
            await session.delete(chunk)
        document = existing
        document.version_date = version_date
        document.source_filename = source_filename
        document.chunk_count = 0
    else:
        document = Document(
            law_name=law_name,
            version_date=version_date,
            source_filename=source_filename,
        )
        session.add(document)
        await session.flush()

    collection = get_collection()
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for piece in chunks:
        chroma_id = make_chroma_id()
        db_chunk = Chunk(
            document_id=document.id,
            chroma_id=chroma_id,
            law_name=piece.law_name,
            article_number=piece.article_number,
            chapter=piece.chapter,
            content=piece.content,
            version_date=piece.version_date,
        )
        session.add(db_chunk)
        ids.append(chroma_id)
        documents.append(piece.content)
        metadatas.append(
            {
                "law_name": piece.law_name,
                "article_number": piece.article_number,
                "chapter": piece.chapter,
                "version_date": piece.version_date,
            }
        )

    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    document.chunk_count = len(chunks)
    await session.commit()
    await session.refresh(document)
    return document


async def delete_document(session: AsyncSession, document_id: int) -> None:
    document = await session.get(Document, document_id)
    if not document:
        raise ValueError("法律文档不存在")

    collection = get_collection()
    for chunk in list(document.chunks):
        collection.delete(ids=[chunk.chroma_id])
        await session.delete(chunk)

    await session.delete(document)
    await session.commit()


async def list_documents(session: AsyncSession) -> list[Document]:
    result = await session.scalars(select(Document).order_by(Document.law_name))
    return list(result.all())


async def get_chunk_by_chroma_id(session: AsyncSession, chroma_id: str) -> Chunk | None:
    return await session.scalar(select(Chunk).where(Chunk.chroma_id == chroma_id))


def citations_to_json(citations: list[Citation]) -> str:
    return json.dumps([citation.to_dict() for citation in citations], ensure_ascii=False)
