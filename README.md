# Caremate AI

**Phase 1 — Core AI/LLM Engineering Layer** ✓

A safety-checked, provider-agnostic RAG and agent pipeline for healthcare assistance.
Built with a six-agent deterministic pipeline, structured output schemas, and
comprehensive guardrails.

## Quick Start (Zero API Keys Required)

```bash
# Install dependencies
python -m pip install -e ".[dev]"

# Run tests (27 tests, all using the mock provider)
pytest tests/ -v

# Interactive demo
python -m caremate.cli
```

## Architecture

### Provider Abstraction
- `LLMProvider` / `EmbeddingProvider` abstract base classes
- Implementations: OpenAI, Anthropic, Groq, Mock (for offline testing)

### RAG Pipeline
- Section-aware medical document chunking
- Patient-isolated FAISS vector store
- Hybrid retrieval + reranking

### Six-Agent Pipeline
1. **Document Agent** → pre-process & extract metadata
2. **Retrieval Agent** → retrieve relevant chunks
3. **Summarization Agent** → summarize + generate reasoning
4. **Citation Agent** → verify & format citations
5. **Safety Agent** → injection detection, red-flag symptoms, drug-food interactions
6. **Response Agent** → assemble typed `StructuredAIResponse`

### Guardrails
- Prompt-injection detection (regex + semantic)
- Red-flag symptom detection
- Drug-food interaction checking

### Nutrition Feature
- Patient Q&A with structured, cited responses
- Silent doctor-side malnutrition risk watcher

## Testing
- 27 automated tests covering patient isolation, citation verification,
  adversarial prompt-injection resistance, and red-flag short-circuiting
- All tests pass with zero API keys (uses Mock provider)