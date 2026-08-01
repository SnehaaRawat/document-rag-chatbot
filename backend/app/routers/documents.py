import os
import uuid

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import asc

from app.database import get_db
from app.config import get_settings
from app.models import Document, Chunk, DocumentStatus
from app.schemas import DocumentOut, ChunkOut
from app.ingestion import process_document
from app.chunking import SUPPORTED_EXTENSIONS

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


@router.post("/upload", response_model=list[DocumentOut])
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    os.makedirs(settings.upload_dir, exist_ok=True)
    created: list[Document] = []

    for file in files:
        ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                400,
                f"Unsupported file type for {file.filename}. Accepted: "
                f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}.",
            )

        file_bytes = await file.read()
        if len(file_bytes) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(400, f"{file.filename} exceeds the {settings.max_upload_mb}MB upload limit.")

        # content_type here is just a display/tracking label (the extension),
        # not used for parsing dispatch — extract_pages() dispatches on the
        # actual filename extension so this staying simple is fine.
        resolved_content_type = ext

        document = Document(
            id=str(uuid.uuid4()),
            filename=file.filename,
            content_type=resolved_content_type,
            status=DocumentStatus.processing,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        created.append(document)

        # Chunking + embedding happens after the response so uploads feel instant.
        background_tasks.add_task(
            process_document, document.id, file_bytes, resolved_content_type, file.filename
        )

    return created


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.created_at.desc()).all()


@router.get("/{document_id}/chunks", response_model=list[ChunkOut])
def get_document_chunks(document_id: str, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(404, "Document not found")
    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .order_by(asc(Chunk.chunk_index))
        .all()
    )
    return chunks


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(404, "Document not found")
    db.delete(document)
    db.commit()
