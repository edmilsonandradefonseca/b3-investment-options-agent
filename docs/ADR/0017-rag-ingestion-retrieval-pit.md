# ADR-0017 — RAG minimal ingestion and point-in-time retrieval

**Status:** Accepted  
**Date:** 2026-09-17

## Context

The RAG foundation now has Evidence, metadata, deterministic chunking, an embedding abstraction and a provider-neutral VectorStore implemented by Qdrant. The project intentionally avoids freezing a sophisticated retrieval strategy before exercising real dashboard use cases.

## Decision

Add only the minimum end-to-end path needed to exercise real retrieval:

```text
Evidence
  → Chunking
  → Embedding
  → VectorStore
  → Retrieval
  → Point-in-Time filtering
  → optional freshness metadata
```

The ingestion pipeline is provider-neutral and returns the ingested evidence/chunk identifiers for auditability.

The retrieval facade:
- embeds the query through the configured `EmbeddingProvider`;
- applies caller metadata filters;
- when `as_of` is supplied, constrains publication to `published_at <= as_of` and validity to `valid_at = as_of`;
- optionally calculates a freshness score without changing the semantic similarity score.

## Deliberately deferred

- BM25/hybrid retrieval;
- reranking;
- query rewriting or HyDE;
- learned ranking formulas;
- automatic query/entity extraction;
- production embedding model selection;
- final KnowledgeContext integration.

These are deferred until real dashboard/use-case testing reveals a concrete need.

## Consequence

Qdrant is exercised as an implementation of the VectorStore contract, but application code remains independent of the database vendor. Retrieval can evolve without changing Evidence, Chunking, Embedding or agent contracts.
