import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conversation, Message
from app.schemas import ChatRequest, ChatResponse, SourceOut, MessageOut
from app.rag import answer_question

router = APIRouter(tags=["chat"])


def _sources_to_json(retrieved) -> str:
    return json.dumps([
        {
            "chunk_id": r.chunk.id,
            "document_id": r.document.id,
            "document_filename": r.document.filename,
            "content": r.chunk.content,
            "page_number": r.chunk.page_number,
            "section_title": r.chunk.section_title,
            "similarity": round(r.similarity, 4),
        }
        for r in retrieved
    ])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    if not req.message.strip():
        raise HTTPException(400, "message cannot be empty")

    if req.conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
        if not conversation:
            raise HTTPException(404, "Conversation not found")
    else:
        conversation = Conversation(
            id=str(uuid.uuid4()),
            document_ids=",".join(req.document_ids) if req.document_ids else "",
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    history = [
        {"role": m.role, "content": m.content}
        for m in sorted(conversation.messages, key=lambda m: m.created_at)
    ]

    document_ids = req.document_ids or (
        conversation.document_ids.split(",") if conversation.document_ids else None
    )

    answer, retrieved, grounded = answer_question(db, req.message, document_ids, history)

    user_msg = Message(id=str(uuid.uuid4()), conversation_id=conversation.id, role="user", content=req.message)
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        sources_json=_sources_to_json(retrieved),
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()

    sources = [
        SourceOut(
            chunk_id=r.chunk.id,
            document_id=r.document.id,
            document_filename=r.document.filename,
            content=r.chunk.content,
            page_number=r.chunk.page_number,
            section_title=r.chunk.section_title,
            similarity=round(r.similarity, 4),
        )
        for r in retrieved
    ]

    return ChatResponse(
        conversation_id=conversation.id,
        answer=answer,
        sources=sources,
        grounded=grounded,
    )


@router.get("/chat/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(conversation_id: str, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(404, "Conversation not found")

    result = []
    for m in sorted(conversation.messages, key=lambda m: m.created_at):
        sources = json.loads(m.sources_json) if m.sources_json else None
        result.append(MessageOut(role=m.role, content=m.content, sources=sources, created_at=m.created_at))
    return result
