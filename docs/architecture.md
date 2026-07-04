# Review Discovery Engine — System Architecture

## 1. Overview

The **Review Discovery Engine** is a RAG (Retrieval-Augmented Generation) system that ingests user feedback from **App Store**, **Play Store**, and **Reddit**, stores it in a vector database, and uses **Grok** to answer natural-language questions about user pain points, behaviors, and unmet needs.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (HTML / Tailwind / JS)                   │
│  Query UI · Source filters · Segment explorer · Citation-backed answers     │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ REST / SSE
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                         BACKEND (Python — FastAPI)                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐  │
│  │ Query API   │  │ Ingest API   │  │ Analytics   │  │ Admin / Health   │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └──────────────────┘  │
│         │                │                 │                                │
│  ┌──────▼────────────────▼─────────────────▼──────────────────────────────┐ │
│  │                     Application Services Layer                          │ │
│  │  RAG Orchestrator · Retriever · Prompt Builder · Response Formatter    │ │
│  └──────┬─────────────────────────────────────────────────────────────────┘ │
│         │                                                                    │
│  ┌──────▼──────────┐  ┌─────────────────┐  ┌────────────────────────────┐ │
│  │ Embedding Svc   │  │ Ingestion Svc   │  │ Segmentation & Cluster Svc │ │
│  └──────┬──────────┘  └────────┬────────┘  └────────────────────────────┘ │
└─────────┼──────────────────────┼────────────────────────────────────────────┘
          │                      │
┌─────────▼──────────┐  ┌────────▼───────────────────────────────────────────┐
│   ChromaDB         │  │  External Sources                                  │
│   (Vector Store)   │  │  App Store · Play Store · Reddit API / scrapers    │
└────────────────────┘  └────────────────────────────────────────────────────┘
          │
┌─────────▼──────────┐
│   Grok API (xAI)   │
│   Generation LLM   │
└────────────────────┘
```

---

## 2. Design Goals

| Goal | Approach |
|------|----------|
| **Grounded answers** | Every response cites retrieved review chunks; no unsourced claims |
| **Multi-source synthesis** | Unified schema across App Store, Play Store, Reddit |
| **Segment-aware analysis** | Rich metadata enables filtering by platform, rating, date, inferred segment |
| **Scalable ingestion** | Batch pipeline with idempotent upserts into ChromaDB |
| **Low-latency queries** | Hybrid retrieval (semantic + metadata filters) with optional streaming |
| **Maintainable stack** | Python backend, vanilla frontend, ChromaDB, Grok — per problem statement |

---

## 3. Layered Architecture

### 3.1 Presentation Layer (Frontend)

**Stack:** HTML, Tailwind CSS, vanilla JavaScript

**Responsibilities:**
- Natural-language query input with suggested prompts aligned to discovery questions
- Filters: source (App Store / Play Store / Reddit), date range, star rating, keyword
- Display answers with inline citations linking to source reviews
- Optional: theme cluster view, segment comparison panels, export (JSON/CSV)

**Key pages / modules:**

| Module | Purpose |
|--------|---------|
| `QueryPanel` | Submit questions; show streaming or final answer |
| `CitationDrawer` | Expand retrieved review snippets with source links |
| `FilterBar` | Metadata filters passed to backend |
| `InsightsDashboard` | Pre-computed aggregates (top themes, sentiment by segment) |
| `IngestStatus` | Admin view: last sync, document counts per source |

**Communication:** REST JSON for queries; Server-Sent Events (SSE) optional for streamed Grok responses.

---

### 3.2 API Layer (Backend — FastAPI)

**Recommended framework:** FastAPI (async, OpenAPI docs, SSE support)

**Core endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/query` | RAG query with optional filters |
| `GET` | `/api/v1/query/stream` | SSE stream of generated answer |
| `POST` | `/api/v1/ingest/trigger` | Trigger ingestion job (admin) |
| `GET` | `/api/v1/ingest/status` | Pipeline status and counts |
| `GET` | `/api/v1/reviews/{id}` | Fetch single review by ID |
| `GET` | `/api/v1/analytics/themes` | Top recurring themes (cached) |
| `GET` | `/api/v1/analytics/segments` | Segment breakdown |
| `GET` | `/api/v1/health` | Liveness / dependency checks |

**Cross-cutting concerns:**
- CORS for static frontend
- Rate limiting on query endpoints
- Structured logging (request ID, retrieval latency, token usage)
- Environment-based config via `.env` (Grok API key, Chroma path, Reddit credentials)

---

### 3.3 Application Services Layer

#### 3.3.1 RAG Orchestrator

Central coordinator for the query path:

```
User Question
     │
     ▼
┌─────────────────┐
│ Query Analyzer  │  → intent, entities, implied filters
└────────┬────────┘
         ▼
┌─────────────────┐
│ Retriever       │  → top-k chunks from ChromaDB (+ rerank)
└────────┬────────┘
         ▼
┌─────────────────┐
│ Prompt Builder  │  → system + context + question template
└────────┬────────┘
         ▼
┌─────────────────┐
│ Grok Client     │  → generate answer
└────────┬────────┘
         ▼
┌─────────────────┐
│ Response Formatter│ → answer + citations + confidence note
└─────────────────┘
```

**Query types supported (from problem statement):**

1. Pain-point discovery — *"Why do users struggle to discover new music?"*
2. Feature frustration — *"Most common frustrations with recommendations?"*
3. Behavioral intent — *"What listening behaviors are users trying to achieve?"*
4. Habit / repeat listening — *"What causes users to repeatedly listen to the same content?"*
5. Segment comparison — *"Which user segments experience different discovery challenges?"*
6. Unmet needs synthesis — *"What unmet needs emerge consistently across reviews?"*

The orchestrator selects retrieval strategy based on query type (e.g., segment queries widen metadata filters; synthesis queries increase `top_k` and enable MMR diversity).

#### 3.3.2 Retriever

- **Primary:** ChromaDB similarity search on review embeddings
- **Hybrid enhancement:** BM25 or keyword overlap on `text` field (via Chroma metadata + optional local index) for exact terms like "shuffle", "Discover Weekly"
- **Reranking:** Cross-encoder or Grok-based rerank on top-20 → top-5 (optional phase 2)
- **MMR (Maximal Marginal Relevance):** Reduce redundant chunks in synthesis queries

**Default retrieval parameters:**

| Parameter | Default | Notes |
|-----------|---------|-------|
| `top_k` | 8 | Increase to 15–20 for cross-segment synthesis |
| `similarity_threshold` | 0.65 | Tunable per collection |
| `max_context_tokens` | 6,000 | Leave room for Grok output |

#### 3.3.3 Prompt Builder

System prompt enforces:
- Answer only from provided review excerpts
- Cite sources as `[Source: platform | rating | date | id]`
- Distinguish observation vs inference
- For segment questions: group findings by inferred segment
- Acknowledge gaps when evidence is thin

#### 3.3.4 Ingestion Service

Handles ETL from all sources into a normalized document model before embedding and upsert.

#### 3.3.5 Segmentation Service

Rule-based + LLM-assisted tagging applied at ingest time:

| Segment signal | Inference method |
|----------------|------------------|
| Platform | Source metadata |
| Power user vs casual | Review length, feature mentions, technical language |
| Discovery-focused | Keywords: "discover", "new music", "recommendations" |
| Repeat / comfort listening | Keywords: "same songs", "replay", "comfort" |
| Frustrated user | Low star rating + negative sentiment |

Tags stored as Chroma metadata for filtered retrieval.

---

### 3.4 Data Layer

#### 3.4.1 ChromaDB Schema

**Collection:** `reviews`

Each document = one review or one review chunk (long Reddit posts split).

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable hash: `{source}:{native_id}` |
| `document` | string | Cleaned review text (chunk if split) |
| `embedding` | vector | Generated by embedding model |
| **metadata** | | |
| `source` | enum | `app_store`, `play_store`, `reddit` |
| `app_name` | string | Target app (e.g., Spotify) |
| `rating` | int | 1–5 (nullable for Reddit) |
| `title` | string | Review title or post title |
| `author` | string | Anonymized handle |
| `created_at` | ISO date | Original post date |
| `url` | string | Link to original |
| `language` | string | ISO 639-1 |
| `sentiment` | float | -1 to 1 (computed at ingest) |
| `segments` | string[] | JSON-encoded tags |
| `chunk_index` | int | 0 if single chunk |
| `parent_id` | string | Original review ID if chunked |

**Collections (optional split for scale):**
- `reviews_app_store`
- `reviews_play_store`
- `reviews_reddit`

Or single collection with `source` metadata filter (recommended for MVP).

#### 3.4.2 Embedding Model

Use a cost-effective, locally runnable model to avoid per-query embedding API costs:

- **Recommended:** `sentence-transformers/all-MiniLM-L6-v2` (384-dim, fast)
- **Alternative:** OpenAI-compatible embedding via Grok ecosystem if xAI provides one

Embeddings computed at ingest time and cached; query embeddings computed per request.

#### 3.4.3 Raw Data Storage (Optional)

```
data/
├── raw/           # Original JSON from scrapers/APIs
├── processed/     # Normalized documents pre-embedding
└── chroma/        # Persistent ChromaDB directory
```

File-based staging simplifies re-indexing without re-scraping.

---

## 4. Data Ingestion Pipeline

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  App Store   │   │  Play Store  │   │    Reddit    │
│  Connector   │   │  Connector   │   │  Connector   │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          ▼
              ┌───────────────────────┐
              │  Normalizer           │
              │  (unified schema)     │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │  Cleaner              │
              │  dedupe · lang detect │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │  Enricher             │
              │  sentiment · segments │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │  Chunker              │
              │  512 tokens, 64 overlap│
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │  Embedder             │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │  ChromaDB Upsert      │
              │  (idempotent)         │
              └───────────────────────┘
```

### 4.1 Source Connectors

| Source | Recommended approach | Notes |
|--------|---------------------|-------|
| **App Store** | `app-store-scraper` (Python) or RSS + iTunes Search API | Respect rate limits; store country/locale |
| **Play Store** | `google-play-scraper` | Paginate by sort (newest, rating) |
| **Reddit** | Official Reddit API (PRAW) | Target subreddits: r/spotify, r/music, app-specific subs |

Each connector implements a common interface:

```python
class ReviewConnector(Protocol):
    def fetch(self, since: datetime | None) -> list[RawReview]: ...
```

### 4.2 Normalization

Map all sources to `RawReview`:

```python
@dataclass
class RawReview:
    native_id: str
    source: Literal["app_store", "play_store", "reddit"]
    text: str
    title: str | None
    rating: int | None
    author: str
    created_at: datetime
    url: str
    app_name: str
    locale: str | None
```

### 4.3 Chunking Strategy

| Content type | Strategy |
|--------------|----------|
| Short store reviews (< 300 tokens) | Single chunk, `chunk_index=0` |
| Long Reddit posts / threads | Split at 512 tokens, 64-token overlap; link via `parent_id` |
| Reddit comment threads | Flatten top-level + high-score replies into composite document |

### 4.4 Idempotent Upserts

Document ID = `hash(source + native_id + chunk_index)`. Re-running ingestion updates changed reviews without duplicates.

---

## 5. RAG Query Flow (Detailed)

### 5.1 Request Schema

```json
{
  "question": "Why do users struggle to discover new music?",
  "filters": {
    "sources": ["app_store", "play_store", "reddit"],
    "min_rating": 1,
    "max_rating": 5,
    "date_from": "2024-01-01",
    "date_to": "2026-07-01",
    "segments": ["discovery-focused"],
    "app_name": "Spotify"
  },
  "options": {
    "top_k": 10,
    "stream": false
  }
}
```

### 5.2 Response Schema

```json
{
  "answer": "Users frequently cite ...",
  "citations": [
    {
      "id": "reddit:abc123_0",
      "excerpt": "...",
      "source": "reddit",
      "rating": null,
      "url": "https://...",
      "relevance_score": 0.82
    }
  ],
  "metadata": {
    "retrieved_count": 10,
    "sources_used": ["reddit", "play_store"],
    "model": "grok-3",
    "latency_ms": 2340
  }
}
```

### 5.3 Grok Integration

- **Client:** xAI REST API (`https://api.x.ai/v1/chat/completions`)
- **Model:** Latest Grok chat model (e.g., `grok-3` or current production alias)
- **Config:** Temperature 0.2 for factual synthesis; max tokens 1,024
- **Fallback:** Return retrieval-only summary if Grok unavailable

---

## 6. Analytics & Pre-computed Insights

To support dashboard views without repeated LLM calls:

| Job | Frequency | Output |
|-----|-----------|--------|
| Theme extraction | Weekly | Top N themes with example review IDs |
| Sentiment by source | Daily | Aggregates in JSON cache |
| Segment distribution | Weekly | Counts per segment tag |
| Trending frustrations | Daily | Keyword frequency delta |

Implementation: lightweight batch script reading from ChromaDB metadata + optional Grok batch summarization; results stored in `data/analytics/` and served via `/api/v1/analytics/*`.

---

## 7. Project Structure

```
review-analyzer/
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── styles.css          # Tailwind build output
│   ├── js/
│   │   ├── api.js
│   │   ├── query.js
│   │   ├── citations.js
│   │   └── dashboard.js
│   └── assets/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entry
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── query.py
│   │   │   ├── ingest.py
│   │   │   └── analytics.py
│   │   ├── services/
│   │   │   ├── rag_orchestrator.py
│   │   │   ├── retriever.py
│   │   │   ├── prompt_builder.py
│   │   │   ├── grok_client.py
│   │   │   └── embedder.py
│   │   ├── ingestion/
│   │   │   ├── pipeline.py
│   │   │   ├── normalizer.py
│   │   │   ├── chunker.py
│   │   │   └── connectors/
│   │   │       ├── app_store.py
│   │   │       ├── play_store.py
│   │   │       └── reddit.py
│   │   ├── models/
│   │   │   └── schemas.py
│   │   └── db/
│   │       └── chroma_client.py
│   ├── scripts/
│   │   ├── run_ingestion.py
│   │   └── run_analytics.py
│   ├── requirements.txt
│   └── .env.example
├── data/
│   ├── raw/
│   ├── processed/
│   ├── chroma/
│   └── analytics/
├── architecture.md
├── problemstatement.md
└── README.md
```

---

## 8. Technology Choices & Rationale

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Backend | **FastAPI** | Async I/O, typing, auto OpenAPI, SSE |
| Vector DB | **ChromaDB** | Required by spec; embedded, persistent, metadata filters |
| LLM | **Grok (xAI)** | Required by spec; strong reasoning for synthesis |
| Embeddings | **sentence-transformers** | Local, free, sufficient for review similarity |
| Frontend | **HTML + Tailwind + JS** | Required by spec; no build complexity for MVP |
| Task runner | **APScheduler** or cron | Scheduled ingestion/analytics jobs |

---

## 9. Security & Compliance

- Store API keys in `.env`; never commit secrets
- Anonymize author handles in API responses (hash or truncate)
- Respect platform ToS for scraping; prefer official APIs where available
- Rate-limit external API calls and user query endpoints
- Log retention policy for query audit trails (optional)

---

## 10. Deployment Architecture

### 10.1 Local / MVP

```
Docker Compose (optional):
  - backend: Python FastAPI on :8000
  - frontend: nginx static on :3000
  - chroma: embedded persistent volume
```

### 10.2 Production (Future)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  CDN / Nginx│────▶│  FastAPI    │────▶│  ChromaDB   │
│  (static)   │     │  (2+ replicas)│   │  (persistent│
└─────────────┘     └──────┬──────┘     │   volume)   │
                           │            └─────────────┘
                           ▼
                    ┌─────────────┐
                    │  xAI Grok   │
                    └─────────────┘
```

---

## 11. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Query latency (p95) | < 5 s including Grok |
| Ingestion throughput | 10k reviews / hour |
| Availability | 99% (single-instance MVP) |
| Data freshness | Daily incremental sync |
| Answer grounding | 100% answers include ≥ 1 citation |

---

## 12. Implementation Phases

### Phase 1 — Foundation (MVP)
- ChromaDB setup + embedding pipeline
- Single source ingest (Play Store)
- Basic RAG query endpoint + Grok integration
- Minimal query UI with citations

### Phase 2 — Multi-source
- App Store + Reddit connectors
- Unified normalizer and metadata filters
- Frontend filter bar

### Phase 3 — Intelligence
- Segmentation tagging
- Analytics jobs (themes, trends)
- Insights dashboard
- Query streaming (SSE)

### Phase 4 — Hardening
- Reranking, MMR, hybrid search
- Docker deployment
- Monitoring and rate limiting

---

## 13. Key Design Decisions Summary

1. **Modular monolith** over microservices — simpler ops for the specified stack
2. **Single Chroma collection with metadata filters** — easier cross-source synthesis queries
3. **Ingest-time enrichment** (sentiment, segments) — faster filtered retrieval at query time
4. **Citation-first prompts** — aligns answers with evidence for trust and auditability
5. **File-based staging** — enables re-embedding without re-scraping
6. **FastAPI backend** — best fit for Python + async Grok/Chroma I/O

This architecture directly supports the six discovery question categories in the problem statement while staying within the mandated tech stack: **HTML, Tailwind, JS · Python · ChromaDB · Grok**.
