# ADR — Shared AI Platform for B3 Runtime

**Status:** Accepted  
**Date:** 2026-09-27

## Context

The Ubuntu host already runs reusable AI infrastructure for João Resolve:

- shared multilingual embedding service
- Qdrant
- Neo4j
- SearXNG

B3 originally introduced a dedicated local Compose stack for Qdrant and Neo4j. That duplicates CPU/RAM usage, creates host-port conflicts and makes service lifecycle ownership ambiguous.

The local embedding runtime was validated on 2026-09-27 as:

- `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- 768 dimensions
- endpoint `http://127.0.0.1:8093`

The same platform is intended to host a future local LLM runtime such as DeepSeek.

## Decision

All reusable infrastructure services on this Ubuntu deployment are shared platform services.

B3 is a consumer, not the lifecycle owner, of:

- embedding service
- Qdrant
- Neo4j
- SearXNG
- future local LLM inference runtime

B3 MUST NOT start, stop, restart, recreate or upgrade those services as part of application startup or preflight.

## Isolation

Sharing service processes does not mean sharing application state.

### Qdrant

- João collections use `joao_` ownership prefixes.
- B3 collections use `b3_` ownership prefixes.
- B3 V4 hybrid collections use explicit 768d dense + sparse schemas.
- Legacy dense-only collections are preserved and are not silently repurposed.

### Neo4j

- João uses the `Entity` label.
- B3 uses the `B3Entity` label.
- B3 constraints and queries are scoped to `B3Entity`.
- B3 lifecycle operations must not delete or mutate João-owned graph data.

### Embeddings

Both applications may call the same 768d embedding service. Vector compatibility is guaranteed only when the same model/configuration contract is in force.

### Future DeepSeek

A future DeepSeek deployment should run once as a shared inference service. João and B3 consume it through explicit routing/contracts rather than loading duplicate model instances.

## Consequences

Positive:

- lower RAM/CPU usage
- no duplicate database/model processes
- one operational surface for shared infrastructure
- simpler health monitoring and upgrades
- consistent 768d embedding space

Constraints:

- application data isolation must be explicit
- service upgrades become platform-level changes
- B3 tests must not assume lifecycle ownership
- destructive smoke tests must use temporary B3-owned resources only

## V4 impact

This decision changes runtime topology and ownership, so it is recorded explicitly rather than treated as an implementation detail.

It does not change the functional UC-01..UC-12 contracts, human decision boundaries, canonical structured truth, or the rule that Qdrant/Neo4j are rebuildable projections.
