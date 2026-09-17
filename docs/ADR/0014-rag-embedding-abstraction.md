# ADR 0014 — RAG Embedding Abstraction

- **Status:** Accepted
- **Date:** 2026-09-17
- **Scope:** RAG foundation, semantic retrieval

## Decision

The RAG pipeline will depend on a provider-neutral `EmbeddingProvider` contract rather than directly on an embedding vendor or model.

The contract accepts an ordered sequence of texts and returns an ordered sequence of `Embedding` values. Each embedding records the model identifier used to create it.

## Rules

1. Embeddings are derived artifacts; canonical `Evidence` and `EvidenceChunk` remain the source records.
2. Provider/model selection is an implementation concern, not a knowledge contract.
3. Batch order must be preserved.
4. Empty input text is invalid.
5. Embedding dimensions must be stable for a configured provider/model in a vector-store integration.
6. Point-in-time and provenance metadata remain attached to the chunk and are not encoded into the vector itself.
7. No production embedding provider is selected in this ADR.
8. A deterministic provider exists only for tests and local contract validation; it is not a semantic search implementation.

## Rationale

This allows later use of OpenAI, local models, Hugging Face or another provider without changing the evidence/chunk contracts or retrieval architecture.

## Non-goals

- vector database
- similarity search
- semantic ranking
- LLM enrichment
- production model selection
