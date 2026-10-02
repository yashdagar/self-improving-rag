# Self-Improving RAG for Scientific Research Literature

A retrieval-augmented generation system that answers AI/ML research questions from **live arXiv papers**, cites every claim to the exact retrieved chunk, **evaluates its own answers**, and uses those evaluations plus user feedback to **change how it ranks evidence** for future questions. A Baseline RAG runs alongside it so the improvement can be measured on real experiments.

## Contents

- [Pipeline](#pipeline)
- [How each stage works](#how-each-stage-works)
- [The self-improvement mechanism](#the-self-improvement-mechanism)
- [Baseline vs proposed](#baseline-vs-proposed)
- [Experiments](#experiments)
- [Setup](#setup)
- [API](#api)
- [Project layout](#project-layout)
- [Configuration](#configuration)
- [Testing and conventions](#testing-and-conventions)
- [Limitations](#limitations)

## Pipeline

```
User query
  → Query analysis            keywords for arXiv (stopword filtering)
  → Live arXiv retrieval      cs.AI, cs.LG, cs.CL, cs.CV, cs.NE, stat.ML, recency window, local cache
  → PDF acquisition           top N papers, abstract fallback
  → Extraction + chunking     PyMuPDF, section detection, paragraph-aware chunks with overlap
  → Embeddings                sentence-transformers, stored in ChromaDB
  → Vector search             cosine similarity over this query's candidate papers
  → Hybrid ranking            α·semantic + β·recency + γ·feedback
  → Grounded generation       LLM answers only from numbered evidence, [n] citations
  → Citation mapping          every [n] mapped to a chunk; invalid markers removed and counted
  → Self-evaluation           LLM judge rates chunks, citations, coverage, relevance
  → Feedback storage          SQLite: query, chunks, scores, answer, evaluation, 👍/👎
  → Adaptive update           α, β, γ move toward what separated relevant evidence
  → Better retrieval next time
```

Everything for one question is stored in SQLite (`data/rag.db`), so any answer can be traced back to the papers, chunks, scores and weights that produced it.

## How each stage works

### 1. Query analysis and live arXiv retrieval
`backend/app/services/query_analysis.py`, `arxiv_client.py`, `paper_retrieval.py`

The question is reduced to up to five keywords (question words and generic research words are dropped). These become an arXiv API query restricted to the six AI/ML categories and a submission-date window:

```
(all:"chain of thought" AND all:llm) AND (cat:cs.AI OR ... OR cat:stat.ML) AND submittedDate:[... TO ...]
```

If the strict `AND` query returns too few papers, the system retries with `OR`. Requests are spaced at least 3 seconds apart (arXiv's guideline), retried with exponential backoff that honours `Retry-After`, and every search result is cached in the `arxiv_search_cache` table so repeated questions make no API calls. Paper metadata (title, authors, abstract, dates, categories, arXiv ID, URLs) lives in `papers`.

### 2. Full text and chunking
`pdf_fetcher.py`, `pdf_extractor.py`, `chunking.py`, `document_processor.py`

The top `PDF_MAX_PAPERS_PER_QUERY` papers have their PDFs downloaded (size-capped, checked to be a real PDF) and parsed with PyMuPDF block by block:

- **Section detection** recognises numbered (`3.2 Training Details`), roman, and named headings (`Related Work`), including headings split across lines.
- **Cleaning** joins hyphenated line breaks and drops figure/table debris (low letter ratio).
- **Bibliography removal** stops at `References`, or when blocks look like reference lists (years, initials, `arXiv preprint`, `pp.`), because reference lists match queries well but contain no findings.

Chunks never cross a section boundary, are cut at sentence boundaries up to `CHUNK_SIZE_CHARS`, and carry `CHUNK_OVERLAP_CHARS` of the previous chunk's last sentences. The abstract is always chunk 0. If the PDF is missing, unreadable or scanned, the paper is stored as `abstract_only` with the reason in `pdf_error`. Each chunk stores paper ID, section, page, source (`pdf`/`abstract`) and position.

### 3. Embeddings and vector search
`embeddings.py`, `vector_store.py`, `indexer.py`

Chunks are embedded with `sentence-transformers/all-MiniLM-L6-v2` (normalised vectors, title and section prepended to the text) and stored in a persistent ChromaDB collection using cosine distance. Search is restricted to the papers retrieved for the current question and returns `RETRIEVAL_CANDIDATE_POOL` candidates with similarity `1 - cosine distance`.

### 4. Hybrid ranking
`ranking.py`, `feedback_scores.py`, `retrieval_pipeline.py`

```
final = α · semantic + β · recency + γ · feedback        α + β + γ = 1,  each in [WEIGHT_MIN, WEIGHT_MAX]
```

- **semantic:** similarity min-max normalised over the candidate pool, so all three terms share the 0 to 1 scale.
- **recency:** `0.5 ^ (age_days / RECENCY_HALF_LIFE_DAYS)`, so a paper loses half its recency score every half-life.
- **feedback:** what past questions taught the system about this chunk (next section). Unknown chunks get the neutral 0.5.

The top `RETRIEVAL_TOP_K` chunks are selected with at most `MAX_CHUNKS_PER_PAPER` from one paper, so the answer draws on several sources. Every component score is saved per retrieved chunk.

### 5. Grounded generation and citations
`generation.py`, `citations.py`, `llm.py`

The selected chunks are numbered `[1]..[k]` with title, arXiv ID, year, section and page. The system prompt requires the model to use only these excerpts, end every factual sentence with the numbers that support it, never cite numbers that were not supplied, and set `insufficient_evidence` with a description of what is missing when the excerpts do not answer the question. Output is structured JSON validated with Pydantic.

The answer is then split into claims (sentences) and every marker is mapped to the exact chunk. Markers that point outside `[1..k]` are removed from the answer and recorded in `invalid_citations`; factual sentences without any valid citation are counted in `uncited_claims`. The system therefore never shows a citation it cannot resolve to stored evidence.

Two LLM providers are supported:
- **anthropic** (default, `claude-opus-5`): official SDK, `messages.parse` structured output, refusal handling via `stop_reason`, and server-side refusal fallbacks (`fallbacks: "default"`) enabled for models that support them.
- **openai_compatible:** any `/chat/completions` endpoint (Ollama, Groq, vLLM, OpenAI), JSON mode plus schema validation with one repair attempt.

### 6. Self-evaluation
`evaluation.py`

A second LLM call acts as a strict judge. It does not output the final scores. It makes small, checkable judgments, and the scores are computed from them in code:

| metric | computed as |
|---|---|
| retrieval precision | share of top-k chunks judged `relevant` to the question |
| retrieval relevance | mean of relevant 1, partial 0.5, irrelevant 0 |
| groundedness | mean over factual claims of the best support among its citations (uncited factual claim = 0) |
| citation accuracy | mean support over every claim→chunk citation, with each invalid marker counted as 0 |
| answer relevance | judge's 0 to 4 rating divided by 4 |
| evidence coverage | share of the question's aspects that the retrieved evidence covers |

The judge's per-chunk relevance and per-citation verdicts are saved on `retrieved_chunks.judged_relevance` and `citations.support`/`verdict_reason`; the six scores, their mean and the reasoning are saved in `evaluations`. Set `EVALUATOR_MODEL` to judge with a different model from the generator.

## The self-improvement mechanism

There are two learning loops, both driven only by stored evaluations and feedback.

**Loop 1: chunk memory (the γ term).** Each past signal about a chunk becomes evidence for its feedback score on future questions:

| signal | value | weight |
|---|---|---|
| 👍/👎 on a specific evidence chunk | 1 / 0 | 1.0 |
| 👍/👎 on the whole answer, applied to the chunks it cited | 1 / 0 | 0.5 |
| judge's relevance rating for a retrieved chunk | 1 / 0.5 / 0 | 0.5 |
| judge's support verdict when the chunk was cited | 1 / 0.5 / 0 | 0.5 |

Each signal is further weighted by how similar its original question is to the current one, `max(0, (cos - τ) / (1 - τ))` with τ = `FEEDBACK_SIMILARITY_THRESHOLD`, so feedback transfers to related questions but not to unrelated ones. The score is a Laplace-smoothed average that starts at the neutral 0.5:

```
feedback(chunk) = (prior · 0.5 + Σ wᵢ · valueᵢ) / (prior + Σ wᵢ)
```

**Loop 2: weight adaptation (α, β, γ).** After each evaluated proposed-mode answer (and after each 👍/👎), `adaptation.py` asks which ranking component actually separated the relevant chunks from the irrelevant ones in that answer's top-k. For each component it computes the regression slope of the component score on the relevance label:

```
slope_c = cov(c, relevance) / var(relevance)
```

Positive slopes are normalised into a target weight vector `w*`, and the weights take one bounded step toward it:

```
w ← (1 − η) · w + η · w*,   then projected so that Σw = 1 and every w ∈ [WEIGHT_MIN, WEIGHT_MAX]
```

`η` is `WEIGHT_LEARNING_RATE`, so no single answer can move a weight by more than η. No update happens if fewer than `ADAPTATION_MIN_LABELS` chunks are labelled, all labels are equal, or no component has a positive slope. Every update writes a row to `weight_snapshots` with the weights before and after, the slopes, the target, the learning rate and the triggering query, so the whole trajectory is auditable at `GET /api/improvement/history`.

Learning is **scoped**: weights and signals belong to either the live system or one experiment run (`experiment_run`), and only proposed-mode queries teach the system. An experiment therefore always starts from the initial weights and learns only from its own history.

## Baseline vs proposed

| | Baseline | Proposed (self-improving) |
|---|---|---|
| arXiv retrieval, PDFs, chunks, embeddings | same | same |
| ranking | semantic only (α = 1, β = γ = 0) | α·semantic + β·recency + γ·feedback |
| generation and citation mapping | same | same |
| self-evaluation | yes, to measure it | yes |
| learns from evaluation and feedback | no | yes |

Both modes share the arXiv cache, so in an experiment they see the same candidate papers and only the ranking differs.

## Experiments

`evaluation/questions.json` holds 24 AI/ML research questions, each with a paraphrase that is never seen during learning.

```bash
.venv/bin/python evaluation/run_experiment.py --run-id my-run --cycles 3 --baseline-cycles 1 --test paraphrase
.venv/bin/python evaluation/plot_results.py my-run
```

The protocol:

1. **Warm-up:** every question and paraphrase is retrieved once, so arXiv results, PDFs and embeddings are cached and both systems see identical candidates.
2. **Training cycles:** each cycle asks every question to the proposed system, which evaluates itself and adapts after every answer. The baseline answers the same questions (it does not learn, so one cycle is enough to measure it; use `--baseline-cycles` to repeat).
3. **Held-out test:** the paraphrased questions go to both systems with learning frozen (`learn=False`). This measures whether what was learned transfers to new wording rather than memorising the training questions.

`run_experiment.py` is resumable (finished steps are skipped) and exports `evaluation/results/<run>/queries.csv` and `summary.json`. `plot_results.py` turns those files into:

- `metrics_by_cycle.png`: the six metrics per cycle, proposed against the baseline.
- `weights.png`: α, β, γ for every proposed-mode query in order.
- `retrieval_change.png`: top-k overlap (Jaccard) with the previous cycle, the direct measure that retrieval behaviour changed.
- `test_comparison.png`: held-out paraphrases, baseline against proposed.
- `latency.png`: mean time per stage.
- `report.md`: the same numbers as tables, plus paired differences with 95% bootstrap intervals and win/loss counts on the held-out set.

Every number comes from stored query records. Nothing in `evaluation/results/` is written by hand. The same per-cycle aggregates are served at `GET /api/experiments/{run}/cycles` for the dashboard.

## Setup

Requires Python 3.11+, Node 20+, and an LLM (an Anthropic API key, or a local model through Ollama).

```bash
./scripts/setup.sh                            # .venv, Python + Node deps, git hooks, .env from .env.example
.venv/bin/python scripts/download_models.py   # optional: fetch the embedding model ahead of time
BACKEND_PORT=8000 ./scripts/dev.sh            # backend on BACKEND_PORT, dashboard http://localhost:5173
```

**Claude (default):** set `LLM_API_KEY=` in `.env` (or export `ANTHROPIC_API_KEY`).

**Local model with Ollama:**

```bash
brew install ollama
OLLAMA_CONTEXT_LENGTH=16384 ollama serve      # the default 4k context truncates the evidence prompt
ollama pull qwen2.5:7b-instruct
```

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://localhost:11434/v1         # http://host.docker.internal:11434/v1 from Docker
LLM_MODEL=qwen2.5:7b-instruct
LLM_MAX_TOKENS=2000
```

**Docker:** `docker compose up --build` (data, the SQLite DB, Chroma and the model cache persist in `./data`).

The database schema is created on startup. There are no migrations; after pulling schema changes, delete `data/rag.db` and `data/chroma` to start fresh.

## API

Interactive docs at http://localhost:8000/docs.

| method | path | purpose |
|---|---|---|
| POST | `/api/query` | run the full pipeline (`mode`: `baseline`/`proposed`, `learn`, `experiment_run`, `cycle`) |
| GET | `/api/query`, `/api/query/{id}` | recent queries, or one with evidence, citations, evaluation, feedback |
| POST | `/api/feedback` | 👍/👎 on an answer or one evidence chunk; triggers a weight update |
| POST | `/api/retrieve` | ranking only, with the score breakdown, no LLM |
| GET | `/api/papers/{id}` | paper metadata and chunks (`?include_chunks=true`); `POST .../process` re-extracts |
| GET | `/api/arxiv/search` | live arXiv search with caching |
| GET | `/api/metrics` | mean scores, latency and feedback per mode (`?experiment_run=`) |
| GET | `/api/improvement/history` | current weights and every weight update with its reasoning |
| GET | `/api/experiments`, `/api/experiments/{run}/cycles` | experiment runs and per-cycle comparison |
| GET | `/api/system/status` | storage, database, vector store, embedding model, LLM, counts |

## Project layout

```
backend/app/
  api/        one router per resource
  core/       settings (validated), SQLite engine, logging
  models/     SQLAlchemy tables: papers, chunks, queries, retrieved_chunks, citations,
              evaluations, feedback, weight_snapshots, arxiv_search_cache, experiment_runs
  schemas/    Pydantic request/response models
  services/   one file per pipeline stage (see above); container.py wires them together
  main.py     app factory
frontend/src/ React dashboard (components, pages, services)
evaluation/   questions.json, run_experiment.py, plot_results.py, results/
scripts/      setup.sh, dev.sh, download_models.py
tests/        pytest suite with fake arXiv, embedder and LLM; no network needed
data/         SQLite DB, Chroma index, PDFs (git-ignored)
```

## Configuration

Every setting is an environment variable (see `.env.example`), validated at startup in `backend/app/core/config.py`. The ones most worth knowing:

- **Retrieval:** `ARXIV_MAX_RESULTS`, `ARXIV_RECENCY_DAYS`, `PDF_MAX_PAPERS_PER_QUERY`, `RETRIEVAL_CANDIDATE_POOL`, `RETRIEVAL_TOP_K`, `MAX_CHUNKS_PER_PAPER`.
- **Ranking:** `ALPHA_INIT`, `BETA_INIT`, `GAMMA_INIT` (must sum to 1), `WEIGHT_MIN`, `WEIGHT_MAX`, `RECENCY_HALF_LIFE_DAYS`.
- **Learning:** `WEIGHT_LEARNING_RATE`, `ADAPTATION_MIN_LABELS`, `FEEDBACK_PRIOR_STRENGTH`, `FEEDBACK_SIMILARITY_THRESHOLD`.
- **LLM:** `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_EFFORT`, `LLM_FALLBACKS`, `EVALUATOR_MODEL`.

API keys are only read from the environment and are never returned by any endpoint.

## Testing and conventions

```bash
.venv/bin/pytest                 # 200+ tests, no network or LLM needed
(cd frontend && npm run build)
```

Commits follow Conventional Commits, enforced by `.githooks/commit-msg`, and source files contain no comments, enforced by `tests/test_code_style.py`. See `CONTRIBUTING.md`.

## Limitations

- The judge is an LLM, and by default the same model as the generator, so self-evaluation can share the generator's blind spots. Use `EVALUATOR_MODEL` to separate them, and read the stored reasoning rather than the numbers alone.
- Weight adaptation learns from the top-k only (chunks the system already chose), so it refines the ranking rather than discovering evidence it never retrieved.
- The training cycles repeat the same questions; the held-out paraphrase test is what shows transfer.
- arXiv keyword search is the recall ceiling: a paper the API does not return cannot be ranked.
- Section detection is heuristic and some PDFs (two-column layouts, scanned papers) fall back to coarser sections or the abstract.
