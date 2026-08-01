import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, Text, ForeignKey, DateTime, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.config import get_settings

settings = get_settings()


def gen_uuid():
    return str(uuid.uuid4())


class DocumentStatus(str, enum.Enum):
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.processing, nullable=False)
    error_message = Column(Text, nullable=True)
    page_count = Column(Integer, nullable=True)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    document_id = Column(UUID(as_uuid=False), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # order within the document
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)   # best-effort page reference
    section_title = Column(String, nullable=True)  # best-effort section/heading
    token_count = Column(Integer, nullable=False)
    embedding = Column(Vector(settings.embedding_dim), nullable=True)

    document = relationship("Document", back_populates="chunks")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    # Conversations are scoped to whichever document(s) were selected when
    # the chat started; document_ids is a simple comma-separated list to
    # keep the schema simple for a demo-scale app.
    document_ids = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    conversation_id = Column(UUID(as_uuid=False), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    # For assistant messages: JSON-encoded list of source chunks used, stored as text
    sources_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="messages")
