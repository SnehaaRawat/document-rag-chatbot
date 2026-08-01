"""
Embedding generation, abstracted behind one function so the rest of the
app doesn't care whether embeddings come from a local model or an API.
"""
from functools import lru_cache

from app.config import get_settings

settings = get_settings()


@lru_cache
def _get_local_model():
    # Imported lazily so `openai`-only deployments don't pay the
    # sentence-transformers/torch import cost on cold start.
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.local_embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns one vector per input text."""
    if not texts:
        return []

    if settings.embedding_provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        # OpenAI embedding endpoint accepts batches directly.
        resp = client.embeddings.create(model=settings.openai_embedding_model, input=texts)
        return [d.embedding for d in resp.data]

    model = _get_local_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
