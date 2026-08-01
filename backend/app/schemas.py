from datetime import datetime
from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    filename: str
    content_type: str
    status: str
    error_message: str | None = None
    page_count: int | None = None
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChunkOut(BaseModel):
    id: str
    chunk_index: int
    content: str
    page_number: int | None = None
    section_title: str | None = None
    token_count: int

    class Config:
        from_attributes = True


class SourceOut(BaseModel):
    chunk_id: str
    document_id: str
    document_filename: str
    content: str
    page_number: int | None = None
    section_title: str | None = None
    similarity: float


class ChatRequest(BaseModel):
    message: str
    document_ids: list[str] | None = None  # None = search across all ready documents
    conversation_id: str | None = None      # None = start a new conversation


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[SourceOut]
    grounded: bool  # False when we returned the "couldn't find this" fallback


class MessageOut(BaseModel):
    role: str
    content: str
    sources: list[SourceOut] | None = None
    created_at: datetime
