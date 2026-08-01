"""
Retrieval + generation.

Design choices (see README for full rationale):
- Similarity search uses pgvector's cosine distance operator (<=>) via the
  SQLAlchemy pgvector integration. We convert distance -> similarity
  (similarity = 1 - distance) so thresholds/scores read intuitively.
- The similarity threshold is a hard gate: if the BEST retrieved chunk is
  below it, we skip the LLM call entirely and return the fixed
  "couldn't find this" response. This is deliberate — it stops the model
  from ever being tempted to answer from parametric knowledge instead of
  the document, which is the main hallucination failure mode in RAG demos.
- Multi-turn memory: prior turns are passed to the LLM as conversation
  history, but retrieval is still keyed off the CURRENT user message only.
  We prepend a short rewritten-standalone-query step so pronouns like
  "what about section 2 of it" resolve against the right chunks.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config import get_settings
from app.embeddings import embed_query
from app.models import Chunk, Document

settings = get_settings()

NOT_FOUND_MESSAGE = "I couldn't find this in the document."


def _get_generation_client_and_model():
    """
    Returns (client, model_name) for whichever generation provider is
    configured. Groq's API is OpenAI-SDK compatible, so both providers
    use the same `openai` client — only the base_url, key, and model
    name differ.
    """
    from openai import OpenAI

    if settings.generation_provider == "groq":
        client = OpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)
        return client, settings.groq_model

    client = OpenAI(api_key=settings.openai_api_key)
    return client, settings.generation_model


@dataclass
class RetrievedChunk:
    chunk: Chunk
    document: Document
    similarity: float


def retrieve(db: Session, query: str, document_ids: list[str] | None, top_k: int) -> list[RetrievedChunk]:
    query_vector = embed_query(query)

    stmt = (
        select(
            Chunk,
            Document,
            Chunk.embedding.cosine_distance(query_vector).label("distance"),
        )
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.status == "ready")
        .order_by("distance")
        .limit(top_k)
    )
    if document_ids:
        stmt = stmt.where(Chunk.document_id.in_(document_ids))

    rows = db.execute(stmt).all()
    return [
        RetrievedChunk(chunk=chunk, document=document, similarity=1 - distance)
        for chunk, document, distance in rows
    ]


def _condense_query(current_message: str, history: list[dict]) -> str:
    """
    For multi-turn follow-ups ("what about the pricing section"), rewrite
    the message into a standalone query using the last couple of turns,
    so vector search doesn't retrieve on a pronoun. Falls back to the raw
    message if there's no history or no API key configured.
    """
    if not history or not settings.generation_configured:
        return current_message

    client, model = _get_generation_client_and_model()
    recent = history[-4:]
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in recent)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": (
                    "Rewrite the final user message as a standalone search query "
                    "that captures its full meaning without needing the prior "
                    "conversation for context. Output ONLY the rewritten query."
                )},
                {"role": "user", "content": f"{transcript}\nuser: {current_message}"},
            ],
            temperature=0,
            max_tokens=80,
        )
        return resp.choices[0].message.content.strip() or current_message
    except Exception:
        return current_message


def generate_answer(question: str, retrieved: list[RetrievedChunk], history: list[dict]) -> str:
    if not settings.generation_configured:
        # No LLM configured — return the top chunk verbatim so the pipeline
        # is still testable end-to-end without any API key.
        top = retrieved[0]
        return (
            "[No generation API key configured — showing the most relevant excerpt "
            f"instead of a generated answer]\n\n{top.chunk.content}"
        )

    client, model = _get_generation_client_and_model()

    context_blocks = []
    for i, r in enumerate(retrieved, start=1):
        loc = f"p.{r.chunk.page_number}" if r.chunk.page_number else "n/a"
        context_blocks.append(f"[Source {i} | {r.document.filename} | {loc}]\n{r.chunk.content}")
    context = "\n\n".join(context_blocks)

    system_prompt = (
        "You are a document Q&A assistant. Answer the user's question using ONLY "
        "the numbered sources below. Cite sources inline like [Source 1] when you "
        "use them. If the sources don't contain the answer, say so plainly instead "
        "of guessing. Never use outside knowledge.\n\n" + context
    )

    messages = [{"role": "system", "content": system_prompt}]
    for m in history[-6:]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": question})

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=600,
    )
    return resp.choices[0].message.content.strip()


def answer_question(
    db: Session,
    question: str,
    document_ids: list[str] | None,
    history: list[dict],
) -> tuple[str, list[RetrievedChunk], bool]:
    """Returns (answer_text, retrieved_chunks_used, grounded)."""
    search_query = _condense_query(question, history)
    retrieved = retrieve(db, search_query, document_ids, settings.top_k)

    if not retrieved or retrieved[0].similarity < settings.similarity_threshold:
        return NOT_FOUND_MESSAGE, [], False

    # Only pass chunks that clear the threshold as context — a top hit can
    # be strong while lower-ranked ones are noise.
    grounded_chunks = [r for r in retrieved if r.similarity >= settings.similarity_threshold]
    answer = generate_answer(question, grounded_chunks, history)
    return answer, grounded_chunks, True
