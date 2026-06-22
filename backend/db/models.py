from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    law_name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    version_date: Mapped[str] = mapped_column(String(50), default="")
    source_filename: Mapped[str] = mapped_column(String(255), default="")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    chroma_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    law_name: Mapped[str] = mapped_column(String(200), index=True)
    article_number: Mapped[str] = mapped_column(String(50), default="")
    chapter: Mapped[str] = mapped_column(String(200), default="")
    content: Mapped[str] = mapped_column(Text)
    version_date: Mapped[str] = mapped_column(String(50), default="")

    document: Mapped["Document"] = relationship(back_populates="chunks")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    response_type: Mapped[str] = mapped_column(String(30), default="answer")
    citations_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
