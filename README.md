# Self-Improving RAG for Scientific Research Literature

A retrieval-augmented generation system that answers AI/ML research questions from live arXiv papers, cites every claim to the exact retrieved chunk, evaluates its own answers, and uses that evaluation plus user feedback to adapt how it ranks evidence on future queries.

## Pipeline

```
User query
  → Query analysis / reformulation
  → Live arXiv retrieval (cs.AI, cs.LG, cs.CL, cs.CV, cs.NE, stat.ML)
  → PDF acquisition (abstract fallback)
  → Text extraction (PyMuPDF) + section-aware chunking
  → Embeddings (sentence-transformers) + ChromaDB vector search
  → Hybrid ranking:  score = α·semantic + β·recency + γ·feedback
  → Grounded LLM generation with inline citations
  → Citation mapping to paper/chunk
  → Self-evaluation (relevance, groundedness, citation accuracy, coverage)
  → Feedback storage (SQLite)
  → Adaptive update of α, β, γ (bounded, learning-rate based)
  → Better retrieval on future queries
```

**Baseline mode:** arXiv → semantic retrieval → generation.
**Proposed mode:** arXiv → semantic retrieval → recency + feedback ranking → generation → evaluation → adaptive update.

## Layout

```
backend/app/
  api/        FastAPI routers (one file per resource)
  core/       settings, logging
  services/   pipeline stages (arxiv, pdf, chunking, embeddings, ranking, llm, evaluation, adaptation)
  models/     SQLAlchemy tables
  schemas/    Pydantic request/response models
  main.py     app factory
frontend/src/
  components/ pages/ services/
evaluation/   research question set + experiment outputs
data/         SQLite db, Chroma index, cached papers and PDFs (git-ignored)
scripts/      setup and dev helpers
tests/        pytest suite
```

## Setup

Requires Python 3.11+ and Node 20+.

```bash
./scripts/setup.sh        # creates .venv, installs deps, copies .env.example to .env
# put your key in .env as LLM_API_KEY
./scripts/dev.sh          # backend on :8000, dashboard on :5173
.venv/bin/pytest          # run tests
```

Or with Docker: `docker compose up --build`.

API docs are served at http://localhost:8000/docs.

## Configuration

All settings live in `.env` (see `.env.example`) and are validated at startup by `backend/app/core/config.py`:

- **Ranking weights:** `ALPHA_INIT`, `BETA_INIT`, `GAMMA_INIT` must sum to 1 and lie inside `[WEIGHT_MIN, WEIGHT_MAX]`.
- **Adaptation:** `WEIGHT_LEARNING_RATE` caps how far the weights move per update.
- **LLM:** `LLM_PROVIDER` is `anthropic` or `openai_compatible` (OpenAI, Groq, Ollama, etc. via `LLM_BASE_URL`). Keys are only read from the environment and never returned by the API.

## Development phases

1. Project setup + architecture ✅
2. Database + FastAPI
3. Live arXiv retrieval
4. PDF extraction + chunking
5. Embeddings + vector database
6. Hybrid ranking
7. Grounded generation + citations
8. Self-evaluation
9. Feedback + adaptive ranking
10. Baseline vs proposed experiments
11. React frontend
12. Dashboard + visualization
13. Testing + documentation

## API (planned)

- `POST /api/query`
- `POST /api/feedback`
- `GET /api/query/{id}`
- `GET /api/papers/{id}`
- `GET /api/metrics`
- `GET /api/improvement/history`
- `GET /api/system/status` (available now)
