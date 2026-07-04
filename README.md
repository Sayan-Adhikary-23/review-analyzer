# Review Discovery Engine

AI-powered RAG system for analyzing user feedback from App Store, Play Store, and Reddit.

## Features

- Multi-source ingestion: Play Store, App Store (iTunes RSS), Reddit (PullPush archive API)
- ChromaDB vector store with local embeddings (`all-MiniLM-L6-v2`)
- RAG query API with OpenAI (`gpt-4o-mini`)
- Light-themed Q&A web UI with citation-backed answers

## Quick start

### 1. Install backend dependencies

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env
```

Set `OPENAI_API_KEY` in `.env`.

### 3. Scrape and index reviews

```bash
python scripts/run_ingestion.py --all
```

### 4. Run the server

```bash
uvicorn app.main:app --reload --app-dir . --port 8080
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080)

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health and dependency status |
| POST | `/api/v1/query` | RAG query |
| POST | `/api/v1/ingest/trigger` | Trigger ingestion |
| GET | `/api/v1/ingest/status` | Indexed document counts |

## Tech stack

- Frontend: HTML, Tailwind CSS, JavaScript
- Backend: Python, FastAPI
- Vector DB: ChromaDB
- LLM: OpenAI
