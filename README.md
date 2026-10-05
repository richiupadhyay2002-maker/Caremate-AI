# Caremate AI

![Pytest](https://github.com/richiupadhyay2002-maker/Caremate-AI/actions/workflows/tests.yml/badge.svg)

A demonstration healthcare application combining a patient and doctor web
frontend with a Python API, persistence layer, and safety-checked, provider-
agnostic RAG and multi-agent pipeline.

> **Medical disclaimer:** Caremate AI is a demonstration and information tool,
> not a medical device or substitute for professional medical advice,
> diagnosis, or treatment. It does not make clinical decisions. For medical
> concerns, consult a qualified healthcare professional; in an emergency,
> contact your local emergency number.
>
> **Synthetic data:** The included demo records, sample patients, reports, and
> screenshots are synthetic demonstration data, not real medical records.
> Do not commit real patient information, credentials, or private uploads.

## Demo

- [Watch or download the Caremate AI demo recording (MP4)](recordings/20261005-2147-18.1466588.mp4)

![Patient care timeline demo screenshot](docs/screenshots/care-timeline-demo.png)

## Features

- **Frontend:** Next.js and React patient and doctor portals for reports,
  timeline, symptom journal, nutrition, and dashboards.
- **API and database:** Python API, SQLAlchemy persistence, SQLite by default,
  Alembic migrations, authentication, and patient-scoped data access.
- **RAG pipeline:** Section-aware document chunking, patient-isolated FAISS
  retrieval, hybrid search, citations, and structured responses.
- **Six-agent workflow:** Document, retrieval, summarization, citation, safety,
  and response agents.
- **Safety checks:** Prompt-injection detection, emergency red-flag symptom
  handling, and drug-food interaction checks.
- **Provider options:** Mock providers for offline development, with optional
  OpenAI, Anthropic, and Groq integrations.

## Quick Start

### Python API and tests

Requires Python 3.10 or newer.

```bash
python -m pip install -e ".[dev]"
pytest -q
python -m caremate.cli
```

Copy `.env.example` to `.env` to configure providers. The mock provider is the
default and does not require API keys.

Run the API from the project root:

```bash
uvicorn caremate.api.asgi:app --reload --port 8080
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

The Next.js development server starts on port 3000 and uses
`http://localhost:8080` for the API by default. Set `NEXT_PUBLIC_API_URL` in
`frontend/.env.local` when the API runs at another URL.

To enable real LLM providers, install the optional integrations with
`python -m pip install -e ".[providers]"` and configure their API keys.

## Safety Test Results

These are pass rates for the small, hand-authored regression examples in the
automated test suite—not clinical performance metrics or guarantees on
unseen inputs:

| Regression check | Passing examples | Observed result |
| --- | ---: | ---: |
| Prompt-injection examples detected | 4/4 | 100% |
| Benign health question not flagged as injection | 1/1 | 100% |
| Red-flag symptom cases short-circuited | 4/4 | 100% |
| Routine nutrition question not short-circuited | 1/1 | 100% |
| Mock provider refused the tested injection prompt | 1/1 | 100% |

These figures describe only the examples in `tests/test_prompt_injection.py`
and `tests/test_red_flag_short_circuiting.py`; they should not be interpreted
as real-world detection or block rates.

## Project Structure

```text
caremate/                 Python API, agents, providers, retrieval, guardrails
  api/                    API endpoints and application setup
  db/                     Database models, repositories, and sessions
  agents/                 Six pipeline agents
  guardrails/             Injection, symptom, and interaction checks
  retrieval/               Chunking, embeddings, and FAISS retrieval
frontend/                 Next.js patient and doctor web application
alembic/                  Database migration configuration
tests/                    Python unit, API, database, and security tests
docs/                     Architecture documentation and demo screenshot
migrations/               Database migration scripts
recordings/               Project demonstration video
```

## Database

The API uses SQLite by default (`caremate.db`) for local development and
supports PostgreSQL with pgvector. Database connections are configured with
`CAREMATE_DATABASE_URL`; database files, vector indexes, local uploads, and
other generated data are ignored by Git.
See [docs/architecture.md](docs/architecture.md) for architecture and
configuration details.

## Continuous Integration

GitHub Actions runs the Python test suite on pushes and pull requests to `main`.
The badge at the top of this README reports the workflow's latest status.
