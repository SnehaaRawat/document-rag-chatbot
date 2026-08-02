"""
Central configuration. Everything that varies between local/dev/prod
is read from environment variables so the same image can be deployed
to Render/Railway without code changes.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database ---
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/rag_chatbot"

    # --- Embeddings ---
    # "local"  -> sentence-transformers/all-MiniLM-L6-v2, runs on CPU, no API cost, 384 dims.
    #             Loads PyTorch into the process — several hundred MB of baseline memory
    #             even before encoding anything. Fine on your own machine or a paid
    #             instance; can exceed memory-constrained free tiers (e.g. Render's
    #             free 512MB) on its own, independent of document size.
    # "openai" -> text-embedding-3-small, 1536 dims, needs OPENAI_API_KEY, no local model.
    # "gemini" -> gemini-embedding-001, needs GEMINI_API_KEY. Google's free tier
    #             (rate-limited, no billing method required) makes this the
    #             recommended default for memory-constrained free-tier deploys — no
    #             local model means no PyTorch memory footprint at all. Defaults to
    #             3072-dim output but is explicitly truncated to 768 in embeddings.py
    #             to match embedding_dim below (Matryoshka representation learning —
    #             the model supports truncating to 768/1536/256 with little quality loss).
    embedding_provider: str = "local"
    local_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_api_key: str = ""
    gemini_embedding_model: str = "models/gemini-embedding-001"

    # --- Generation (the answer-writing LLM) ---
    # "openai" -> requires OPENAI_API_KEY, uses generation_model (e.g. gpt-4o-mini)
    # "groq"   -> requires GROQ_API_KEY, uses groq_model. Groq's API is OpenAI-SDK
    #             compatible (same client, different base_url), and has a free tier
    #             with no billing method required — see app/rag.py::_get_generation_client
    generation_provider: str = "openai"
    openai_api_key: str = ""
    generation_model: str = "gpt-4o-mini"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # --- Chunking ---
    chunk_size_tokens: int = 350
    chunk_overlap_tokens: int = 60

    # --- Retrieval ---
    top_k: int = 5
    similarity_threshold: float = 0.35  # cosine similarity; below this we say "not found"

    # --- Uploads ---
    upload_dir: str = "app/uploads"
    max_upload_mb: int = 25

    # --- CORS ---
    allowed_origins: str = "http://localhost:3000"

    @property
    def embedding_dim(self) -> int:
        # Must match the model in use. If you change embedding_provider
        # after data already exists, you need to re-embed everything —
        # dimensions can't mix in one pgvector column.
        if self.embedding_provider == "openai":
            return 1536
        if self.embedding_provider == "gemini":
            return 768
        return 384

    @property
    def generation_configured(self) -> bool:
        if self.generation_provider == "groq":
            return bool(self.groq_api_key)
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()

