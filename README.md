# Marginal — Document RAG Chatbot

Ask questions about your own PDFs and text files, with every answer grounded in cited
passages. Built as a full-stack demo: FastAPI + pgvector on the backend, Next.js on the
frontend.

```
┌─────────────┐   upload    ┌───────────────┐   embed    ┌──────────────┐
│   Next.js   │ ─────────▶  │   FastAPI     │ ─────────▶ │  pgvector    │
│  frontend   │             │   backend     │            │  (Postgres)  │
│             │ ◀───────── │  chunk/embed/  │ ◀───────── │              │
│             │   chat      │  retrieve/gen │  similarity│              │
└─────────────┘             └───────────────┘   search   └──────────────┘
                                    │
                                    ▼
                            OpenAI (generation,
                            optional for embeddings)
```

## Repo layout

```
backend/            FastAPI app
  app/
    main.py          app entrypoint, CORS, router registration
    config.py        env-driven settings (DB, embedding/LLM provider, chunk/retrieval tuning)
    database.py      SQLAlchemy engine/session + pgvector extension bootstrap
    models.py        Document, Chunk, Conversation, Message
    chunking.py      multi-format extraction (PDF w/ OCR fallback, docx, pptx, xlsx/csv, html, txt/md, images) + paragraph-aware token-windowed chunking
    embeddings.py    pluggable embedding provider (local sentence-transformers | OpenAI)
    ingestion.py     background-task pipeline: extract -> chunk -> embed -> store
    rag.py           retrieval (pgvector cosine search) + grounded generation
    routers/
      documents.py   POST /documents/upload, GET /documents, GET /documents/{id}/chunks
      chat.py        POST /chat, GET /chat/{conversation_id}/messages
  requirements.txt
  Dockerfile
  .env.example

frontend/            Next.js 14 (App Router) + Tailwind
  app/
    page.tsx                    three-pane layout, state, polling
    layout.tsx                  fonts, metadata
    globals.css                 design tokens, the "ink-bar" signature element
    components/
      DocumentLibrary.tsx       upload dropzone + document list with live status
      ChatInterface.tsx         message thread + composer
      SourcesPanel.tsx          retrieved chunks with similarity indicators
      DocumentViewerModal.tsx   "jump to source" — full document with the cited chunk highlighted
    lib/
      api.ts                    typed fetch client for the backend
      types.ts                  shared types mirroring the backend schemas
  .env.local.example

docker-compose.yml    Postgres+pgvector and the backend for local dev
```

## Running locally

### Option A — Docker Compose (backend + db only, fastest way to try the API)

```bash
cp backend/.env.example backend/.env   # add a GROQ_API_KEY (free) or OPENAI_API_KEY for real generation
docker compose up --build
```

The API is now at `http://localhost:8000` (docs at `/docs`).

Then run the frontend separately:

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Visit `http://localhost:3000`.

### Option B — everything local, no Docker

1. Install Postgres 16 locally and enable pgvector (`CREATE EXTENSION vector;` — the app
   also does this automatically on startup if your DB user has permission).
2. Backend:
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env   # set DATABASE_URL to point at your local Postgres
   uvicorn app.main:app --reload
   ```
3. Frontend: same as Option A above.

Without a generation API key set (`GROQ_API_KEY` or `OPENAI_API_KEY`), `/chat` still works
end-to-end (upload, chunk, embed,
retrieve) but returns the raw top-matching chunk instead of a generated answer, so you
can verify the pipeline without any API cost.

## Deployment

**Database → Neon** (recommended over Render's free Postgres, which is deleted after
30 days — Neon's free tier is permanent, no credit card, and supports pgvector)
- Create a project at neon.tech, run `CREATE EXTENSION IF NOT EXISTS vector;` in its SQL
  editor, and copy the connection string for `DATABASE_URL` below.

**Backend → Render or Railway**
- Both platforms build directly from `backend/Dockerfile`.
- Set env vars: `DATABASE_URL` (the Neon connection string, with the driver prefix
  changed to `postgresql+psycopg2://`), `EMBEDDING_PROVIDER`, `GENERATION_PROVIDER`
  (`groq` or `openai`), `GROQ_API_KEY` or `OPENAI_API_KEY`,
  `GENERATION_MODEL`, `ALLOWED_ORIGINS` (your Vercel domain).

**Frontend → Vercel**
- Import the `frontend/` directory as the project root.
- Set `NEXT_PUBLIC_API_URL` to your deployed backend URL.
- Default Next.js build settings work as-is.

## RAG pipeline design choices

**Format support is dispatch-based, not format-specific chunking.** `extract_pages()` in
`app/chunking.py` is the only place that knows about file formats — PDF (with an OCR
fallback via PyMuPDF + Tesseract for scanned pages), Word, PowerPoint, Excel/CSV, HTML,
Markdown/plain text, and standalone images (OCR'd directly). Every format branch reduces
down to the same `RawPage` shape (page/slide/sheet number + text), so chunking, embedding,
retrieval, and citation logic downstream never need to know or care what the original file
was. Adding another format later is one function that returns `list[RawPage]`, not a
change to the pipeline.

**Chunking: paragraph-first, then token-packed with overlap.** Splitting on a fixed
character count is the easiest thing to implement and the fastest way to produce chunks
that cut sentences (and facts) in half. Splitting purely on paragraphs gives semantically
clean chunks but wildly uneven sizes — a one-line paragraph and a 40-line paragraph both
become "one chunk," which hurts retrieval consistency. This app splits the extracted text
into paragraphs/headings first, then packs consecutive paragraphs into ~350-token windows
(configurable), carrying the tail ~60 tokens of one window into the start of the next so a
fact sitting on a paragraph boundary isn't orphaned in a single chunk. A paragraph larger
than the whole budget (a huge run-on block) is hard-split as a fallback.

**Page/section tracking.** PDF text is extracted per-page, so every chunk keeps the page
number(s) it came from. A short, title-cased or markdown-heading-style line is treated as
a section heading and attached to the paragraphs under it. Neither is perfect — PDF page
extraction order can be messy for multi-column layouts, and heading detection is a
heuristic, not a layout parser — but it's enough to give citations a real page reference
instead of "somewhere in the document."

**Embeddings are swappable, dimension-locked.** `EMBEDDING_PROVIDER=local` uses
`sentence-transformers/all-MiniLM-L6-v2` (384-dim, CPU-friendly, no API cost) — the
default so the app runs for free out of the box. `EMBEDDING_PROVIDER=openai` swaps in
`text-embedding-3-small` (1536-dim) for better retrieval quality if you're already paying
for OpenAI generation. The pgvector column's dimension is fixed at table-creation time
from whichever provider is active — switching providers on a database that already has
data requires re-embedding, since the two can't coexist in one column.

**Generation is provider-swappable too.** `GENERATION_PROVIDER=groq` (the default) uses
Groq's API, which is OpenAI-SDK compatible — same client, different `base_url` and model
name — and has a free tier with no billing method required, so the app can give real
generated, cited answers at zero cost out of the box. `GENERATION_PROVIDER=openai` swaps
in OpenAI's models if you'd rather pay for that instead. Both paths share one code path
in `app/rag.py::_get_generation_client_and_model`; adding another OpenAI-compatible
provider (e.g. OpenRouter) is a few lines in that function.

**Retrieval uses pgvector's cosine distance operator directly in SQL** (`embedding <=>
query_vector`, exposed via SQLAlchemy as `.cosine_distance()`), rather than pulling all
vectors into Python and computing similarity there — this lets Postgres do the nearest-
neighbor search and makes it trivial to add an IVFFlat/HNSW index later if the corpus
grows past a few thousand chunks.

**The similarity threshold is a hard gate, not a hint.** If the best-scoring retrieved
chunk is below `SIMILARITY_THRESHOLD` (default 0.35 cosine similarity), the app never
calls the generation model at all — it returns "I couldn't find this in the document"
directly. This is the main anti-hallucination mechanism: an LLM given a weak-but-present
context block will often still try to answer helpfully from its own knowledge, which is
exactly the failure mode a document-grounded chatbot needs to avoid. Chunks that do clear
the bar are passed to the model with an explicit "use ONLY these sources" system prompt
and inline `[Source N]` citation instructions, so the UI's citations correspond to what
the model was actually shown.

**Multi-turn memory + query condensing.** Conversation history is stored per-conversation
and replayed to the generation model so follow-ups read naturally. But retrieval is keyed
off the *current* message's embedding, and a pronoun-heavy follow-up ("what about section
2 of it?") would retrieve badly on its own — so before searching, a lightweight LLM call
rewrites the current message into a standalone query using the last couple of turns. If no
generation API key is configured this step is skipped and the raw message is used directly.

## API reference

| Method | Path | Description |
|---|---|---|
| POST | `/documents/upload` | Multipart upload, one or more files. Returns immediately with `status=processing`; chunking/embedding runs in the background. |
| GET | `/documents` | List all documents with status and chunk counts. |
| GET | `/documents/{id}/chunks` | Inspect how a document was chunked — used by the "jump to source" viewer. |
| DELETE | `/documents/{id}` | Remove a document and its chunks. |
| POST | `/chat` | `{ message, conversation_id?, document_ids? }` → `{ answer, sources, grounded, conversation_id }`. Omit `document_ids` to search across every ready document. |
| GET | `/chat/{conversation_id}/messages` | Full message history for a conversation, with sources. |

## Known limitations

- The mobile layout collapses the document library and sources panel rather than making
  them fully responsive drawers — fine for a demo, worth revisiting for production.
- Heading detection for section titles is a regex heuristic, not a real layout parser; it
  works reasonably on text-first PDFs and plain text, less well on heavily columnar or
  image-heavy PDFs.
- No auth/multi-user isolation — documents and conversations are global to the deployment.
- OCR (scanned PDFs and image uploads) runs through Tesseract, which is solid for clean,
  high-contrast scans but degrades on handwriting, low-resolution photos, or skewed pages —
  expect it to occasionally miss or mangle text on those.
- CSV/Excel extraction converts each sheet to row-by-row text rather than a structured
  query path, so it's good for "what's the value in row X" style questions but not for
  aggregate questions ("what's the average of column Y") — that would need a separate
  structured-query tool, not semantic retrieval.
