# B3 Architecture V4.0 — Implementation Status

**Date:** 2026-09-26  
**Architecture:** V4.0 — APPROVED / FROZEN  
**Current phase:** Phases 1–8 — COMPLETE ON `main`  
**Implementation baseline:** commit `26cd213e62ee4b6889ce2ac2c9a2d3b2496e38a8`

## Executive status

The V4 contract-first implementation has progressed through all eight planned implementation blocks.

| Phase | Capability | Status |
|---|---|---:|
| 1 | Canonical domain contracts | **DONE / FROZEN** |
| 2 | Historical experience substrate / PIT reconstruction | **DONE** |
| 3 | Structured learning | **DONE** |
| 4 | Hybrid experience retrieval | **DONE** |
| 5 | Memory projection / Neo4j bridge | **DONE** |
| 6 | LangGraph PRE-ANALYSIS + POST-OUTCOME learning | **DONE** |
| 7 | Strategy comparison + scenario/stress | **DONE** |
| 8 | V4 dashboard + change detection | **DONE** |

The remaining work is no longer “implement the V4 skeleton”. It is **hardening, retrieval-quality evaluation, data-provider integration, statistical calibration, provenance/evidence refinement and end-to-end validation against UC-01…UC-12**.

## Phase 1 — Canonical Domain Contracts

Implemented and merged:

- `Operation`, `OperationStatus`, `OperationDirection`;
- `FeatureSnapshot`, `FeatureValue`, `FeatureDomain`;
- `Outcome`, `OutcomeStatus`;
- `MarketRegime`, `RegimeDimension`, `RegimeDimensionName`;
- `Learning`, `LearningStatus`, `LearningScope`;
- `LearningEvidenceLink`, `LearningLifecycleTransition`;
- `ExperienceMatch`, `ExperienceRetrievalResult`, `ExperienceAssessment`.

Key commit: `4c2f131aef79abf4545f7d9fe486519678d6f616`.

## Phase 2 — Historical Experience Substrate

Implemented:

```text
Historical transactions
→ Operation Reconstruction
→ PIT Feature Snapshot Builder
→ Outcome Engine
→ Market Regime Reconstruction
→ OutcomeFinalized event
```

Key commit: `14c650c702c30e5ca9431c873bf73d5e800fae5c`.

Point-in-time boundaries are covered by tests. Historical reconstruction must continue to use information availability rather than hindsight.

## Phase 3 — Structured Learning

Implemented canonical experience/learning engine and tests.

Key commit: `7fec8b67dcb4079a37824221dbeb3fcb408e6f01`.

The architecture invariant remains:

> LLMs may propose/interpret learnings; deterministic services own measurable state transitions and validated outcomes.

## Phase 4 — Hybrid Experience Retrieval

Implemented hybrid experience retrieval integrated into `KnowledgeContext`, including B3 768-dimensional semantic memory support and canonical-ID propagation.

Key commit: `8cecba2118931237d19c1c0a76389c44c7deb4fc`.

The frozen retrieval direction is:

```text
Query understanding / filters
        ↓
Dense semantic retrieval
+
Sparse / lexical retrieval
        ↓
Fusion (RRF or calibrated equivalent)
        ↓
Bounded candidate set
        ↓
Deterministic/contextual reranking
        ↓
ExperienceAssessment
```

Qdrant is a candidate-retrieval layer, not the final authority for truth or relevance.

Target reranking signals include:

- semantic relevance;
- lexical relevance;
- strategy/context match;
- market-regime similarity;
- temporal relevance / aging;
- evidence confidence;
- informational value;
- graph relevance.

Weights are configuration/calibration concerns and must not be treated as immutable architecture constants.

## Phase 5 — Memory Projection

Implemented V4 graph schema extensions, Neo4j store/projection bridge and learning relationships.

Key commit: `3fe7ae654a6eb7e330f8fbd71b477d6cd2c6389c`.

Persistence ownership remains:

```text
SQLite / Parquet = canonical structured truth
Qdrant            = reconstructible retrieval projection
Neo4j             = reconstructible relationship projection
```

Canonical IDs and versions must be propagated across stores. Projection failure is degraded indexing, not loss of canonical truth.

## Phase 6 — LangGraph Learning Workflows

Implemented:

- PRE-ANALYSIS experience retrieval;
- V4 experience services;
- KnowledgeContext without Obsidian dependency;
- POST-OUTCOME LangGraph learning workflow;
- canonical learning evidence flow.

Key commit: `032d1ddabaa83e07caad3ef7dbf69b01e86fbd1d`.

Obsidian is not part of the V4 target runtime architecture.

## Phase 7 — Strategy Comparison and Stress

Implemented V4 scenario and strategy-comparison contracts/services and validation tests.

Key commit: `f2824ffb7c04b842e58c64066bddfe148e733cd5`.

Scenario is treated as a first-class, reusable, provenance-aware domain concept rather than an untracked parameter bag.

## Phase 8 — Dashboard and Change Detection

Implemented:

- `AnalysisRun`;
- deterministic change detection;
- V4 dashboard presentation contracts;
- React dashboard redesign for V4 intelligence surfaces;
- frontend build validation in CI.

Key commit: `26cd213e62ee4b6889ce2ac2c9a2d3b2496e38a8`.

## V4 architecture hardening decisions

The following refinements are part of the frozen V4 direction:

1. **Hybrid retrieval:** dense + sparse + metadata filters + fusion + reranking.
2. **Point-in-time context:** historical reasoning must use `available_at <= as_of`; event time alone is insufficient.
3. **Memory authority:** structured persistence owns state; Qdrant and Neo4j are rebuildable projections.
4. **Canonical identity:** cross-store records share stable canonical IDs and explicit versions.
5. **Outcome ≠ evaluation:** objective result and later interpretation remain separate concepts.
6. **Use ≠ confirmation:** retrieval/use frequency cannot reinforce a learning by itself.
7. **Aging is typed:** news/market observations decay differently from facts, lessons and durable relationships.
8. **Contradictions survive:** contradicted/superseded knowledge remains available for audit and historical reasoning.
9. **Claim/evidence provenance:** research should progressively distinguish source document, claim and supporting/contradicting evidence.
10. **Explainable response:** material analyses must expose evidence, risks/limitations, data freshness and trace identifiers.
11. **LLM proposes; services commit state.**
12. **Human remains final investment decision authority.**

## Next implementation gate — V4.1 hardening

The next work should be treated as V4 hardening / V4.1 candidates, not as a restart of V4 implementation:

```text
A. Evaluate dense-only vs dense+sparse vs fusion+reranking
B. Add retrieval traces and benchmark corpus
C. Calibrate aging / regime / strategy relevance
D. Strengthen Claim ↔ Evidence ↔ Source provenance
E. Validate point-in-time replay end-to-end
F. Validate scenario/stress against historical episodes
G. Measure decision-usefulness without self-reinforcement
H. Reconcile all 12 approved use cases against implemented code
I. Run full regression/CI and freeze the verified baseline
```

Recommended retrieval evaluation metrics:

- Precision@K;
- Recall@K where labels permit;
- MRR;
- NDCG;
- evidence utilization;
- retrieval/reranking latency;
- human usefulness;
- decision-usefulness (kept distinct from truth confidence).

## Architecture freeze

V4.0 remains **APPROVED / FROZEN**.

Material changes to canonical contracts, persistence ownership, workflow authority, memory topology or human-decision boundaries require architecture review/ADR. Calibration of retrieval weights, thresholds and ranking profiles is implementation/evaluation work unless it changes those boundaries.
