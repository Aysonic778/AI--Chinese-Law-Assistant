from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None


class CitationResponse(BaseModel):
    law: str
    article: str
    chunk_id: str
    excerpt: str
    version_date: str = ""


class ChatResponse(BaseModel):
    type: str
    content: str
    referenced_laws: list[str]
    citations: list[CitationResponse]
    grounding_score: float
    refusal_reason: str | None = None
    conversation_id: int | None = None


class DocumentResponse(BaseModel):
    id: int
    law_name: str
    version_date: str
    source_filename: str
    chunk_count: int


class ChunkResponse(BaseModel):
    law_name: str
    article_number: str
    chapter: str
    content: str
    version_date: str


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    response_type: str
    citations: list[CitationResponse]
    created_at: str


class ConversationSummary(BaseModel):
    id: int
    title: str
    updated_at: str
    message_count: int


class ConversationDetail(BaseModel):
    id: int
    title: str
    messages: list[MessageResponse]
