# Vectorless RAG — Multi-Tenant Document Chat

A full-stack web application that lets you upload PDFs and chat with them using retrieval-augmented generation — **without vector embeddings**. All search runs on PostgreSQL's built-in full-text engine (tsvector/tsquery) with custom BM25 scoring. No Pinecone, no Weaviate, no ChromaDB.

## What It Does

1. **Sign in** via Clerk (email, Google, GitHub — all supported)
2. **Upload a PDF** — the system extracts text, builds a document tree, generates recursive LLM summaries, and computes BM25 term statistics
3. **Chat with the document** — ask questions in natural language, get cited answers with page numbers
4. **Admin panel** — view all users, delete users (cascades to Clerk + all data), see usage stats
5. **LLM-as-Judge evaluation** — every answer is scored by GPT-4o across four dimensions (faithfulness, groundedness, citation accuracy, relevance), displayed in a collapsible side panel

## Architecture

```
┌─────────────────────┐     ┌──────────────────────────────────┐
│   React + Vite SPA  │────▶│  FastAPI Backend                  │
│   (Clerk Auth)      │     │  • JWT verification               │
│   (React Query)     │     │  • RBAC + tenant isolation         │
└─────────────────────┘     │  • Document CRUD                  │
                            │  • Chat + retrieval               │
                            │  • Admin API                      │
                            └──────────┬───────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
            ┌──────────┐      ┌──────────┐      ┌──────────────┐
            │PostgreSQL│      │  Redis   │      │ Backblaze B2 │
            │(NeonDB)  │      │(broker + │      │(PDF storage) │
            │All data  │      │ cache)   │      └──────────────┘
            │+ FTS     │      └────┬─────┘
            └──────────┘           │
                          ┌────────▼────────┐
                          │  Celery Worker   │
                          │  • PDF extraction │
                          │  • Chunking       │
                          │  • Summarization  │
                          │  • BM25 indexing  │
                          └─────────────────┘
```

### No Vector Embeddings

This is the core differentiator. Instead of embedding models and vector databases, the system uses:

- **PostgreSQL tsvector/tsquery** for full-text search
- **Custom BM25 scoring** with pre-computed term frequencies and IDF stored in `bm25_stats`
- **ILIKE fallback** with word-boundary matching and token-coverage scoring
- **Recursive LLM summaries** stored in `document_trees` for hierarchical traversal (deferred per MVP scope)

All retrieval data lives in PostgreSQL — chunks, trees, BM25 stats, summaries, citations, chat history. Zero external search costs.

## Project Structure

```
vectorlessragcommandcode/
├── backend/
│   ├── app/
│   │   ├── api/           # Route handlers (documents, chat, admin, auth)
│   │   ├── auth/          # Clerk JWT, tenant context, RBAC
│   │   ├── db/            # SQLAlchemy session + base
│   │   ├── ingestion/     # PDF extraction, chunking, tree building, indexing
│   │   ├── models/        # SQLAlchemy ORM models (7 tables)
│   │   ├── retrieval/     # BM25 search, ranker, engine, evaluator, summarizer
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   ├── services/      # Business logic (document, chat, admin, storage)
│   │   ├── tasks/         # Celery config + ingestion tasks
│   │   ├── config.py      # Environment-driven settings
│   │   ├── dependencies.py # Rate limiting, shared dependencies
│   │   └── main.py        # FastAPI app factory
│   ├── alembic/           # Database migrations
│   ├── tests/             # pytest suite (13 tests)
│   ├── requirements.txt
│   └── .gitignore
├── frontend/
│   ├── src/
│   │   ├── api/           # Axios client + API modules
│   │   ├── components/    # UI components (layout, chat, documents, common)
│   │   ├── hooks/         # React Query hooks
│   │   ├── pages/         # Page components (dashboard, documents, chat, admin, profile)
│   │   ├── types/         # TypeScript interfaces
│   │   └── App.tsx        # Root with Clerk auth + routing
│   ├── package.json
│   └── .gitignore
├── .env.example
├── .gitignore
├── LICENSE (MIT)
└── README.md
```

## Database Schema

All data lives in PostgreSQL. Seven tables form the complete data model:

| Table | Purpose |
|:---|:---|
| `users` | Clerk ID, email, role (admin/user), tenant_id |
| `documents` | Filename, B2 key, status (pending→processing→ready→failed), metadata |
| `document_trees` | Hierarchical nodes (document→section→subsection→paragraph), LLM summaries |
| `chunks` | Raw text, page numbers, heading paths, search_vector (tsvector) |
| `bm25_stats` | Term frequency, document frequency, IDF scores per term |
| `chat_sessions` | User sessions scoped to documents, titles, timestamps |
| `chat_messages` | Role (user/assistant), content, citations, retrieval metadata, LLM evaluation scores |

### Multi-Tenant Isolation

Every table carries a `tenant_id` column (= `clerk_user_id` for MVP). All queries filter on it — no data leak possible. Two users uploading the same PDF get fully independent copies with separate UUIDs, chunks, tree nodes, and BM25 rows.

## Features

### Phase 1: Foundation
- Clerk authentication with JWT verification (RS256, JWKS key rotation)
- Auto-registration: users created on first auth via tenant middleware
- Backblaze B2 file storage with local fallback (dev-friendly)
- Full CRUD API for documents
- React + Vite + Tailwind CSS v4 frontend

### Phase 2: Ingestion Pipeline
- Async PDF processing via Celery + Redis (9-stage pipeline)
- PyMuPDF text extraction at block level
- Hierarchical chunking (paragraph splitting, heading detection, max 1500 chars)
- 3-depth document tree (document → page → paragraph)
- Recursive summarization via gpt-4o-mini (bottom-up, batched 5-per-call)
- BM25 indexing: tsvector population + term frequency + IDF computation
- Status polling (pending → extracting → chunking → summarizing → indexing → ready)
- Tenant-isolated ingestion (two users = two independent document copies)

### Phase 3: Retrieval + Chat
- **BM25 lexical search**: PostgreSQL FTS (`websearch_to_tsquery`) + ILIKE fallback with word-boundary matching
- **Parallel FTS + ILIKE**: both run simultaneously, merged per-chunk with best-score wins
- **First-line boost**: 10× multiplier for matches in chunk's opening sentence
- **Token-coverage threshold**: queries must match ≥50% of tokens to avoid noise
- **Confidence threshold** (0.5): discriminates relevant vs. off-topic queries
- **Result fusion**: content deduplication, score ranking, citation building
- **Relevance guardrail**: gpt-4o-mini classifier rejects off-topic questions before retrieval
- **Cache-hit detection**: Jaccard similarity on normalized queries (threshold 0.6)
- **Conversation memory**: sliding window of last 10 messages
- **Citation formatting**: `[Page N]` inline citations with heading paths
- **Chat session CRUD**: create, list, get (with messages), delete

### Phase 4: Admin + Polish
- **Admin API**: list all users (cross-tenant), delete user with full cascade
- **Clerk-integrated deletion**: admin delete → Clerk API delete → Clerk webhook → DB cleanup
- **Redis rate limiting**: sliding window (60 req/min/user, 10 uploads/hour), graceful Redis-unavailable fallback
- **structlog JSON logging**: structured logs with request IDs and correlation context
- **Global error handler**: consistent error schema, never leaks stack traces
- **DB health check**: `/health` probes PostgreSQL connectivity
- **AdminGuard**: frontend route protection, redirects non-admins
- **Admin dashboard**: stats cards, user table, delete with confirmation modal, toast notifications

### Phase 5: LLM-as-Judge Evaluation
- **Four-dimension scoring** by GPT-4o: Faithfulness, Groundedness, Citation Accuracy, Relevance (0-100)
- **Refusal detection**: 11 pattern-matched phrases auto-scored `{0,0,0,0}` (no LLM call wasted)
- **Garbled text penalty**: corrupted/repeated tokens scored under 30
- **Collapsible side panel**: per-message score cards + session average, color-coded bars
- **Scores stored on chat_messages**: persist across page reloads, no re-scoring needed

## API Endpoints

### Documents
| Method | Route | Auth |
|:---|:---|:---|
| `GET` | `/api/v1/documents` | User |
| `POST` | `/api/v1/documents/upload` | User |
| `GET` | `/api/v1/documents/{id}` | User |
| `DELETE` | `/api/v1/documents/{id}` | User |
| `GET` | `/api/v1/documents/{id}/status` | User |

### Chat
| Method | Route | Auth |
|:---|:---|:---|
| `POST` | `/api/v1/chat/sessions` | User |
| `GET` | `/api/v1/chat/sessions` | User |
| `GET` | `/api/v1/chat/sessions/{id}` | User |
| `POST` | `/api/v1/chat/sessions/{id}/messages` | User |
| `DELETE` | `/api/v1/chat/sessions/{id}` | User |

### Admin
| Method | Route | Auth |
|:---|:---|:---|
| `GET` | `/api/v1/admin/stats` | Admin |
| `GET` | `/api/v1/admin/users` | Admin |
| `DELETE` | `/api/v1/admin/users/{id}` | Admin |

### Auth
| Method | Route | Auth |
|:---|:---|:---|
| `GET` | `/api/v1/auth/me` | Any |
| `POST` | `/api/v1/auth/webhook` | Clerk Webhook Secret |

### System
| Method | Route | Auth |
|:---|:---|:---|
| `GET` | `/health` | None |

## How to Run Locally

### Prerequisites
- Python 3.13+
- Node.js 22+
- Redis (Valkey 9+ recommended)
- PostgreSQL (NeonDB free tier works)

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd vectorlessragcommandcode

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Fill in your values

# Frontend
cd ../frontend
npm install
```

### Environment Variables
See `.env.example` for all required variables. Key ones:

| Variable | Description |
|:---|:---|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg-compatible) |
| `REDIS_URL` | Redis connection string |
| `CLERK_SECRET_KEY` | Clerk Backend API secret key |
| `CLERK_JWKS_URL` | Clerk JWKS endpoint for JWT verification |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o / GPT-4o-mini |
| `B2_KEY_ID` / `B2_APP_KEY` | Backblaze B2 credentials (optional, local fallback exists) |

### Running

```bash
# Terminal 1: Backend API
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery Worker
cd backend
.venv/bin/celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2

# Terminal 3: Flower (Celery monitoring)
cd backend
.venv/bin/celery -A app.tasks.celery_app flower --port=5555

# Terminal 4: Frontend
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser. Sign in, upload a PDF, start chatting.

### Running Tests

```bash
cd backend
pytest tests/ -v
```

## Deployment (Railway)

Deploy as three services from the same repository:

| Service | Start Command | 
|:---|:---|
| **API** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Worker** | `celery -A app.tasks.celery_app worker --loglevel=info` |
| **Flower** | `celery -A app.tasks.celery_app flower --port=$PORT --basic-auth=admin:yourpassword` |

Use Railway's **shared variables** for all environment variables. All three services need `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `CLERK_*`, and `B2_*` variables.

Set up a Clerk webhook at `https://your-app.railway.app/api/v1/auth/webhook` for `user.created` and `user.deleted` events.

## Tech Stack

**Backend**: FastAPI, SQLAlchemy (async), PostgreSQL (asyncpg), Celery, Redis, PyMuPDF, LangChain, Boto3 (S3), structlog, pytest

**Frontend**: React 19, Vite 8, TypeScript 6, Tailwind CSS v4, Clerk, React Query, React Router, Axios, Lucide Icons, react-hot-toast

**Infrastructure**: NeonDB (dev), Railway (prod), Backblaze B2 (storage), Clerk (auth)

## License

MIT — see [LICENSE](LICENSE) for details.
