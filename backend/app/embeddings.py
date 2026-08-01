"""
Embedding generation, abstracted behind one function so the rest of the
app doesn't care whether embeddings come from a local model or an API.
"""
from functools import lru_cache

from app.config import get_settings

settings = get_settings()

# Embedding a whole document's chunks in one call spikes memory
# proportionally to document size — a large upload could otherwise create
# a single multi-hundred-chunk batch. Capping the sub-batch size bounds
# peak memory to roughly one batch's worth, regardless of document size.
# This matters most on memory-constrained deploys (e.g. Render's free
# 512MB tier), where the local sentence-transformers/torch model already
# has a sizeable baseline footprint before any encoding happens.
_EMBED_BATCH_SIZE = 32


@lru_cache
def _get_local_model():
    # Imported lazily so `openai`-only deployments don't pay the
    # sentence-transformers/torch import cost on cold start.
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.local_embedding_model)


def _embed_batch(texts: list[str]) -> list[list[float]]:
    if settings.embedding_provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.embeddings.create(model=settings.openai_embedding_model, input=texts)
        return [d.embedding for d in resp.data]

    if settings.embedding_provider == "gemini":
        # google-generativeai is a lightweight REST-based SDK — no PyTorch, no local
        # model weights, so it doesn't carry the memory footprint the local provider does.
        # embed_content accepts a list of strings directly and embeds them all in ONE
        # HTTP call (returns a BatchEmbeddingDict) — looping one call per chunk here
        # would turn a 100-chunk document into 100 sequential round trips, which is
        # what was making ingestion slow before this fix.
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        result = genai.embed_content(model=settings.gemini_embedding_model, content=texts)
        return result["embedding"]

    model = _get_local_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts in fixed-size sub-batches so peak memory doesn't scale
    with document size — a 500-chunk document costs the same peak memory
    as a 32-chunk one, just more wall-clock time."""
    if not texts:
        return []

    results: list[list[float]] = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        results.extend(_embed_batch(texts[i:i + _EMBED_BATCH_SIZE]))
    return results


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]

