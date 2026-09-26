# ADR-0021 — Hybrid Retrieval, Evidence Ranking and Memory Authority

**Status:** Accepted  
**Date:** 2026-09-26  
**Change class:** C7 — Architecture  
**Related architecture:** `docs/ARCHITECTURE_V4.0.md`

## Context

Architecture V4.0 requires retrieval of prior experience, research and learnings under point-in-time constraints. Dense vector similarity alone is insufficient for the B3 domain because queries frequently contain:

- exact tickers and option symbols;
- strategy names;
- strike / expiry identifiers;
- market-regime constraints;
- temporal constraints;
- structured portfolio context;
- historical outcomes;
- provenance and confidence requirements.

The system also requires recency-aware learning without discarding older evidence that remains relevant under a recurring market regime.

## Decision

B3 adopts a **hybrid retrieval and evidence-ranking pipeline**.

The canonical direction is:

```text
Query / Intent
      ↓
Query Understanding
      ↓
Metadata / PIT Filters
      ↓
┌──────────────────────┐
│ Dense Retrieval      │ semantic meaning
│ Sparse Retrieval     │ lexical/exact terms
└──────────┬───────────┘
           ↓
Fusion / RRF
           ↓
Bounded candidate set
           ↓
Context enrichment
           ├── strategy match
           ├── market-regime similarity
           ├── temporal relevance
           ├── evidence confidence
           ├── informational value
           └── graph relationships
           ↓
Deterministic / calibrated reranking
           ↓
ExperienceRetrievalResult
           ↓
ExperienceAssessment
           ↓
KnowledgeContext / reasoning
```

Qdrant retrieves candidates. Its vector score is not the final truth or relevance score.

## Dense retrieval

Dense embeddings are used for semantic similarity, paraphrase matching and concept-level retrieval.

Target V4 embedding baseline remains:

```text
sentence-transformers/paraphrase-multilingual-mpnet-base-v2
768 dimensions
cosine distance
collection: b3_memory_768
```

Dense retrieval is especially useful when the query and evidence use different wording but describe similar situations.

## Sparse retrieval

Sparse / lexical retrieval is required for exact or discriminative tokens such as:

- `PETR4`;
- `TOTS3`;
- option symbols;
- strategy labels;
- named events;
- explicit numerical/contract identifiers.

The concrete sparse implementation may evolve (for example BM25, SPLADE or Qdrant-supported sparse vectors) without changing this ADR.

## Filters

Filters are part of retrieval semantics, not an afterthought.

Examples include:

- canonical entity/ticker;
- memory/evidence type;
- strategy;
- operation type;
- portfolio/user scope;
- market regime;
- source;
- confidence;
- validity;
- `available_at <= as_of`;
- version/status.

A semantically similar record outside the valid point-in-time or domain scope must not outrank a valid record merely because its embedding is closer.

## Fusion

Dense and sparse candidates are combined through Reciprocal Rank Fusion (RRF) or a calibrated equivalent.

Fusion parameters are implementation configuration, not fixed architecture constants.

## Reranking

The final ranking may combine separate signals such as:

```text
retrieval relevance
strategy/context match
market-regime similarity
temporal relevance
evidence confidence
informational value
graph relevance
```

No single universal weighting formula is frozen by this ADR.

Ranking profiles may later become intent-aware, for example:

- investment decision;
- research question;
- historical replay;
- risk analysis.

Such calibration must remain observable and versioned.

## Temporal aging

Aging is typed and context-aware.

The system distinguishes:

- source freshness;
- memory age;
- last confirmation;
- contradiction history;
- regime recurrence.

A record does not become “truer” because it is frequently retrieved.

```text
retrieval_count != confirmation_count
decision_use_count != confirmation_count
```

Confirmation requires new evidence/outcome or another explicit validation path.

Older evidence may regain relevance when regime/context similarity is high.

## Outcome and usefulness

The architecture distinguishes:

```text
truth confidence
retrieval relevance
decision usefulness
historical association
```

A profitable outcome does not prove every supporting memory was correct. A loss may have high informational value.

Outcome attribution must therefore remain explicit and uncertainty-aware.

## Memory authority

The persistence ownership rule is frozen as:

```text
SQLite / Parquet = authoritative structured state
Qdrant            = reconstructible retrieval projection
Neo4j             = reconstructible relationship projection
```

Cross-store objects use stable canonical IDs and explicit versions.

If Qdrant/Neo4j disagree with canonical structured state, canonical structured state wins and the projection is considered stale/degraded.

## Projection consistency

Agents must not independently write authoritative state to all stores.

Preferred flow:

```text
Domain Service
    ↓
Canonical structured commit
    ↓
Event / Outbox
    ├── Vector projector → Qdrant
    └── Graph projector  → Neo4j
```

Projection writes must be idempotent, retryable, observable and rebuildable.

## Point-in-time invariant

Historical retrieval must use information that was available at the analysis timestamp.

At minimum, the system distinguishes:

- event/observation time;
- publication/availability time;
- ingestion time;
- analysis `as_of`.

The rule is:

> historical analysis may not consume evidence whose `available_at` is later than the requested `as_of`.

This protects historical replay, backtesting and learning evaluation against look-ahead bias.

## Research provenance

Research should progressively distinguish:

```text
Source Document
      ↓
Claim
      ↓
Evidence
```

A document may contain multiple claims. A claim may be supported or contradicted by multiple evidence items.

Learning and reasoning should reference canonical evidence/claim identities rather than treating an entire document as an indivisible truth unit.

## Explainability and retrieval traces

Material retrieval runs should preserve enough trace information to answer:

- which filters were applied;
- how many dense/sparse candidates were returned;
- which candidates survived fusion;
- which reranking signals affected ordering;
- which evidence items reached the LLM;
- which canonical IDs and versions were used.

Recommended evaluation metrics include:

- Precision@K;
- Recall@K where labeled;
- MRR;
- NDCG;
- evidence utilization;
- retrieval and reranking latency;
- human usefulness.

## Consequences

### Positive

- better exact-symbol and semantic retrieval;
- reduced dependence on cosine similarity alone;
- explicit PIT correctness;
- observable and tunable ranking;
- protection against self-reinforcing memory loops;
- clearer storage ownership and disaster recovery;
- better provenance and explainability.

### Costs

- sparse index implementation/maintenance;
- fusion/reranking evaluation;
- retrieval trace storage;
- benchmark/query set maintenance;
- additional calibration work.

## Rejected alternatives

### Dense-only retrieval

Rejected because exact symbols, strategy identifiers and lexical evidence are important in the B3 domain.

### Sparse-only retrieval

Rejected because semantically equivalent situations frequently use different language.

### Qdrant score as final relevance

Rejected because relevance also depends on structured context, regime, time, confidence and relationships.

### Retrieval frequency as reinforcement

Rejected because it creates self-reinforcing feedback loops.

### Direct multi-store writes from agents

Rejected because partial failures create inconsistent state and unclear ownership.

## Compatibility

This ADR refines and is compatible with:

- ADR-0020 Continuous Learning & Experience Memory;
- V4 Phase 4 Hybrid Experience Retrieval;
- V4 Phase 5 Memory Projection;
- V4 Phase 6 LangGraph learning workflows;
- the target no-Obsidian runtime direction.

## Next work

1. benchmark dense-only vs hybrid retrieval;
2. introduce/complete sparse retrieval where not already implemented;
3. version retrieval/reranking profiles;
4. persist retrieval traces;
5. calibrate aging/regime/strategy signals;
6. strengthen Claim ↔ Evidence ↔ Source provenance;
7. validate PIT replay end-to-end.
