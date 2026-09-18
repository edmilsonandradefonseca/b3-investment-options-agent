# ADR-0018 — Unified KnowledgeContext Contract

**Status:** Accepted  
**Date:** 2026-09-17

## Context

The approved RAG/KG strategy defines `KnowledgeContext` as the interface between knowledge sources and the investment agents. It must combine deterministic context, RAG evidence and Knowledge Graph context without making the dashboard or individual agents depend directly on vector storage or graph storage.

The context must also preserve point-in-time correctness, provenance and enough metadata for later freshness/confidence handling.

## Decision

`KnowledgeContext` is the bounded integration contract with these logical sections:

- `query`
- `as_of`
- `rag`
- `entities`
- `relations`
- `events`
- `sources`
- `freshness`
- `confidence`
- `deterministic_context`
- `metadata`

The builder accepts optional `as_of` and `deterministic_context` arguments so existing callers remain valid.

When `as_of` is supplied, graph entities and relations are included only when their `as_of`, `valid_from` and `valid_to` fields are compatible with that timestamp. This is a knowledge-layer PIT guard; provider-specific market-data PIT validation remains authoritative at the deterministic data boundary.

Market events are exposed separately from ordinary entities, while retaining their graph identity and provenance.

The builder does not calculate investment metrics, call an LLM, rank opportunities or execute orders.

## Compatibility

Existing `KnowledgeContextBuilder.build(query, rag_top_k=..., graph_top_k=..., neighbor_depth=...)` calls remain valid. New fields have defaults and therefore do not require immediate changes to all callers.

## Consequences

### Positive

- One stable interface for agents.
- Clear separation between RAG, KG and deterministic data.
- Point-in-time validation is explicit at the knowledge boundary.
- Provenance/source references remain available for audit.
- Later Qdrant semantic retrieval and Neo4j persistence can plug into the contract without changing agent interfaces.

### Deferred

- Direct Qdrant retrieval integration into `KnowledgeContextBuilder`.
- Neo4j-backed graph retrieval.
- Production freshness scoring and confidence aggregation.
- LLM enrichment and investment reasoning integration.

These remain subsequent steps and are not part of RAG-06.

## Reference

The design follows `B3_RAG_KG_STRATEGY_V1.0`, particularly the KnowledgeContext section and the roadmap item for integrated deterministic + RAG + KG context.
