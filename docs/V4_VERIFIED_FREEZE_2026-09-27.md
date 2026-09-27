# B3 Architecture V4 — Verified Freeze Record

**Date:** 2026-09-27  
**Status:** VERIFIED / READY TO MERGE  
**Branch:** `docs/v4-architecture-hardening`  
**Verified head before freeze record:** `8866b6ae488248f732ec36b50fa8618777d0926a`  
**Pull request:** #24

## Verification

- Architecture V4.0 remains APPROVED / FROZEN.
- V4 implementation Phases 1–8 are complete.
- Hybrid retrieval direction is dense + sparse + filters + RRF/fusion + deterministic/contextual reranking.
- New semantic memory uses 768-dimensional embeddings.
- Point-in-time availability includes publication, retrieval and validity boundaries.
- SQLite/Parquet remain canonical structured authority; Qdrant and Neo4j are reconstructible projections.
- Obsidian is not part of the V4 target runtime.
- Historical usefulness is separated from truth confidence and is opt-in for ranking.
- Source Document → Claim → Evidence provenance supports explicit SUPPORTS/CONTRADICTS links.
- Retrieval benchmark harness covers Precision@K, Recall@K, MRR, NDCG@K and latency.
- UC-01…UC-12 traceability has been reconciled against the implemented V4 baseline.

## CI evidence

Consecutive successful workflow runs on the hardening branch:
- run 826 — usefulness block — SUCCESS
- run 827 — provenance block — SUCCESS
- run 828 — benchmark + traceability reconciliation — SUCCESS

At the verified head, PR #24 was reported by GitHub as:
- mergeable: true
- mergeable_state: clean
- base: main

## Deferred calibration / production validation

These items do not reopen V4 architecture:
- build a labeled retrieval corpus from real B3 queries/evidence;
- calibrate retrieval/reranking weights and latency trade-offs;
- validate PIT replay against production historical provider timestamps;
- expand statistical Factor Intelligence and multiple-testing safeguards;
- validate scenario/stress models against historical episodes;
- continue provider/data-quality integration.

These are V4.x hardening/calibration activities over the frozen V4 architecture.

## Freeze decision

The V4 architecture and implemented hardening baseline are considered complete for merge. New material changes to canonical contracts, persistence ownership, workflow authority, memory topology or human-decision boundaries require a new ADR/review rather than extending this freeze.
