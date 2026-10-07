# Caremate AI — Architecture

## Overview

Caremate AI is a safety-checked, provider-agnostic RAG (Retrieval-Augmented Generation)
and multi-agent pipeline for healthcare. The system is designed to run with **zero API
keys** using mock providers, with the ability to swap in real LLM providers (OpenAI,
Anthropic, Groq) when API keys are available.

## Core Design Principles

### 1. Zero-API-Key Operation
Every component defaults to mock providers (`MockLLMProvider`, `MockEmbeddingProvider`),
which produce deterministic, reproducible outputs. The `LLMFactory` auto-selects the
appropriate provider based on available API keys, falling back to "mock" when none are
configured.

### 2. Patient Isolation as Architectural Invariant
Patient data isolation is enforced at multiple layers:
- **DocumentChunk** model requires a non-empty `patient_id`
- **PatientIsolatedVectorStore** rejects chunks with empty `patient_id` (raises `ValueError`)
- Search queries are automatically filtered to the requesting patient's data
- 5 dedicated tests verify no cross-patient leakage

### 3. Structured Output Everywhere
The system never returns raw text. All responses are `StructuredAIResponse` objects
containing:
- `response`: The human-readable answer
- `citations`: List of `Citation` objects linking to source material
- `confidence`: A float (0.0–1.0) indicating response confidence
- `safety_flags`: List of safety concerns detected
- `metadata`: Additional context

### 4. Guardrails Short-Circuit Architecture
The `SafetyAgent` runs three safety checks and can short-circuit the pipeline before
response generation:
1. **Prompt Injection Detection** — regex + semantic matching against known injection patterns
2. **Red Flag Symptoms** — 21 medical symptom patterns with severity levels
3. **Drug-Food Interactions** — knowledge base for 20+ medications

## Architecture Layers

The Caremate AI system is organized into seven layers:

1. **CLI Layer** (`cli.py`) — Interactive REPL for demo and testing
2. **Pipeline Layer** (`pipeline.py`) — Orchestrates 6 agents in sequence
3. **Agents Layer** (`agents/`) — 6 specialized agents (Document, Retrieval, Summarization, Citation, Safety, Response)
4. **Retrieval Subsystem** (`retrieval/`) — Chunking, vector storage, hybrid retrieval, embeddings
5. **Guardrails Subsystem** (`guardrails/`) — Injection detection, red flag symptoms, drug-food interactions
6. **Providers Subsystem** (`providers/`) — LLM and embedding providers with factory auto-selection
7. **Models + Nutrition** (`models/`, `nutrition/`) — Data models and nutrition QA/malnutrition monitoring

### Pipeline Flow

```
Document → Retrieval → Summarization → Citation → Safety → Response
                                        │
                              short_circuit (if safety threat)
```

## Component Details

### Models (`caremate/models/`)

| File | Key Classes |
|------|-------------|
| `response.py` | `StructuredAIResponse`, `Citation`, `SafetyFlag`, `SafetyCheckResult` |
| `patient.py` | `PatientContext`, `MedicationEntry`, `AllergyEntry` |
| `document.py` | `DocumentChunk`, `DocumentMetadata` |

### Providers (`caremate/providers/`)

| File | Description |
|------|-------------|
| `base.py` | `LLMProvider`, `EmbeddingProvider` ABCs with structured output support |
| `mock.py` | Deterministic providers using SHA-256 seeded RNG + bag-of-words hashing |
| `openai.py` | OpenAI GPT + text-embedding-3-small provider |
| `anthropic.py` | Anthropic Claude provider |
| `groq.py` | Groq Llama fast inference provider |
| `sentence_transformer.py` | Local sentence-transformers embedding provider |
| `factory.py` | `LLMFactory` with auto-selection and caching |

### Retrieval (`caremate/retrieval/`)

| File | Description |
|------|-------------|
| `chunker.py` | `SectionAwareChunker` — 18 medical section patterns, overlap chunking |
| `vector_store.py` | `PatientIsolatedVectorStore` — in-memory FAISS + patient_id filtering (used by the standalone `CarematePipeline`/CLI) |
| `retriever.py` | `HybridRetriever` — BM25 + embedding similarity fusion |
| `embeddings.py` | `EmbeddingManager` — caching layer over embedding providers |

### Guardrails (`caremate/guardrails/`)

| File | Description |
|------|-------------|
| `prompt_injection.py` | `PromptInjectionDetector` — 19 regex patterns + semantic similarity |
| `red_flag_symptoms.py` | `RedFlagDetector` — 21 symptom patterns, 3 severity levels |
| `drug_food_interactions.py` | `DrugFoodInteractionChecker` — 20+ medication interactions |

### Agents (`caremate/agents/`)

| File | Description |
|------|-------------|
| `base.py` | `BaseAgent` ABC and `PipelineData` dataclass |
| `document_agent.py` | Chunks raw text into DocumentChunks |
| `retrieval_agent.py` | Retrieves relevant chunks from vector store |
| `summarization_agent.py` | Summarizes retrieved content via LLM |
| `citation_agent.py` | Generates verifiable citations with text snippets |
| `safety_agent.py` | Runs all 3 guardrail checks, sets short_circuit flag |
| `response_agent.py` | Assembles final `StructuredAIResponse` |

### Nutrition (`caremate/nutrition/`)

| File | Description |
|------|-------------|
| `database.py` | Food groups, condition-specific dietary recommendations |
| `qa.py` | `NutritionQA` — query interface using the pipeline |
| `malnutrition_watcher.py` | Silent doctor-side alerts based on labs, BMI, weight loss |

## Configuration

Settings are loaded from environment variables with sensible defaults.
A `.env` file is supported via `python-dotenv` (loaded automatically at import time).

| Variable | Default | Description |
|----------|---------|-------------|
| `CAREMATE_LLM_PROVIDER` | `mock` | LLM provider: mock, openai, anthropic, groq |
| `CAREMATE_EMBEDDING_PROVIDER` | `mock` | Embedding provider selection |
| `OPENAI_API_KEY` | (none) | OpenAI API key |
| `ANTHROPIC_API_KEY` | (none) | Anthropic API key |
| `GROQ_API_KEY` | (none) | Groq API key |
| `CAREMATE_VECTOR_DIM` | `384` | Embedding vector dimension |
| `CAREMATE_TOP_K` | `5` | Number of chunks to retrieve |
| `CAREMATE_LOG_LEVEL` | `INFO` | Logging level |

## Testing

- Run the suite with `pytest tests/ -v`; GitHub Actions also runs it on pushes
  and pull requests to `main`.
- The regression tests use mock providers and do not require API keys.

## Security & Privacy (Phase 5)

### TLS & Reverse Proxy

In production, terminate TLS at a reverse proxy (Caddy, Nginx, or a cloud
load balancer) before forwarding to the Uvicorn worker:

```
Client → [TLS] → Reverse Proxy → [HTTP] → Uvicorn (ASGI) → App
```

The application sets `Strict-Transport-Security` (HSTS) and other security
headers automatically via middleware. Ensure the reverse proxy injects
`X-Forwarded-Proto` so the app can enforce HTTPS redirects if needed.

### Security Modules

| Module | Purpose |
|--------|---------|
| `caremate/security/redaction.py` | PII/PHI regex patterns + `PhiRedactionFilter` logging filter |
| `caremate/security/audit.py` | `AuditLogger` writing to the `AuditLog` table |
| `caremate/security/authorization.py` | RBAC + patient-ownership FastAPI dependencies |
| `caremate/security/signed_urls.py` | HMAC-SHA256 signed URLs for time-limited document access |
| `caremate/security/retention.py` | GDPR data deletion, export, and retention policy |

### Security Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAREMATE_JWT_SECRET` | (random) | JWT signing secret; auto-generated if unset |
| `CAREMATE_FORCE_PROD_SECRETS` | `false` | Refuse startup if JWT secret is unset/default |
| `CAREMATE_ENCRYPTION_KEY` | (none) | Fernet key for at-rest field encryption |

## Data Flow Example

1. User submits a medical query through the CLI or NutritionQA
2. **DocumentAgent** chunks any raw documents (using `SectionAwareChunker`)
3. **RetrievalAgent** builds a hybrid index (BM25 + embedding similarity) and retrieves top-k relevant chunks. The CLI pipeline uses the in-memory FAISS store; the API uses the database-backed `PgVectorStore` (`caremate/db/vector_store.py`: pgvector on PostgreSQL, cosine similarity computed in Python on SQLite)
4. **SummarizationAgent** condenses retrieved content via LLM
5. **CitationAgent** generates verifiable citations with source snippets
6. **SafetyAgent** runs 3 checks (injection, red-flag symptoms, drug-food interactions)
   - If any serious threat detected → short-circuit → return safe refusal
7. **ResponseAgent** assembles final `StructuredAIResponse` with citations, confidence, and safety flags

If nutrition-related, the `MalnutritionWatcher` runs silently afterward, generating
doctor-only alerts based on albumin levels, weight loss, BMI, and appetite assessment.






