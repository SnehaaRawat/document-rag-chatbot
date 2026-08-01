"""
The ingestion pipeline: upload -> chunk -> embed -> store.

Runs as a FastAPI BackgroundTask so the upload endpoint can return
immediately with status="processing" while chunking/embedding happens
(embedding a large PDF can take a while, especially on CPU with the
local model). The frontend polls GET /documents to watch status flip
to "ready".
"""
from sqlalchemy.orm import Session

from app.config import get_settings
from app.chunking import extract_pages, chunk_document
from app.embeddings import embed_texts
from app.models import Document, Chunk, DocumentStatus
from app.database import SessionLocal

settings = get_settings()


def process_document(document_id: str, file_bytes: bytes, content_type: str, filename: str) -> None:
    """
    Runs in a background task with its own DB session (the request's
    session is closed by the time this runs).
    """
    db: Session = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return

        pages = extract_pages(file_bytes, content_type, filename)
        if not pages:
            document.status = DocumentStatus.failed
            document.error_message = "No extractable text found in file."
            db.commit()
            return

        raw_chunks = chunk_document(
            pages,
            chunk_size_tokens=settings.chunk_size_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
        )
        if not raw_chunks:
            document.status = DocumentStatus.failed
            document.error_message = "Document produced no chunks after splitting."
            db.commit()
            return

        # Batch-embed all chunk texts in one call for efficiency.
        vectors = embed_texts([c.content for c in raw_chunks])

        for idx, (raw_chunk, vector) in enumerate(zip(raw_chunks, vectors)):
            db.add(Chunk(
                document_id=document.id,
                chunk_index=idx,
                content=raw_chunk.content,
                page_number=raw_chunk.page_number,
                section_title=raw_chunk.section_title,
                token_count=raw_chunk.token_count,
                embedding=vector,
            ))

        document.page_count = len(pages)
        document.chunk_count = len(raw_chunks)
        document.status = DocumentStatus.ready
        db.commit()

    except Exception as exc:  # noqa: BLE001 — surface any failure onto the document row
        db.rollback()
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = DocumentStatus.failed
            document.error_message = str(exc)[:500]
            db.commit()
    finally:
        db.close()
