# ADR-0020 — Continuous Learning & Experience Memory

**Status:** Proposed  
**Date:** 2026-09-26  
**Change class:** C7 — Architecture

## Context

The approved functional baseline in `USE_CASES_INVESTMENT_OPTIONS_V2.0.md` expands the B3 Agent beyond deterministic portfolio/options analysis and conversational explanation.

The approved use cases require the system to:

- reconstruct historical operations with point-in-time context;
- relate operation outcomes to market, macro, flow, commodity, volatility and event conditions;
- identify reusable patterns;
- preserve supporting and contradicting evidence;
- update confidence as new operations arrive;
- account for recency, market regime and concept drift;
- retrieve prior experience before new analyses;
- avoid recomputing the same learning from scratch every time.

The current V3.1 architecture already provides strong foundations:

- B3 Orchestrator Server;
- LangGraph orchestration;
- deterministic engines;
- point-in-time semantics;
- Qdrant vector-store foundation;
- Knowledge Graph contracts with temporal validity;
- KnowledgeContext combining deterministic context, RAG and graph context;
- information lifecycle / freshness decay;
- Risk Validation;
- human decision boundary.

However, V3.1 does not yet define an explicit closed learning loop from real operations and outcomes back into future analysis.

## Decision

The next B3 architecture revision will introduce **Continuous Learning & Experience Memory** as a first-class architectural capability.

The system will preserve the existing V3.1 boundaries and add the following closed loop:

```text
Current State
    ↓
Feature Snapshot + Market Regime
    ↓
Prior Experience Retrieval
    ↓
Analysis / Opportunity / Decision Support
    ↓
Operation
    ↓
Outcome
    ↓
Experience
    ↓
Learning
    ↓
Statistical Validation
    ↓
Aging / Confidence / Drift
    ↓
Hybrid Memory
    ↓
Future Analysis
    ↺
```

This is an architectural evolution of V3.1, not a rewrite.

## Canonical concepts

The next architecture will incorporate the following concepts directly into the architecture model:

### Operation
Represents one economic investment/options operation, potentially composed of multiple broker transactions.

### FeatureSnapshot
Immutable point-in-time representation of the relevant state of the world for an operation or analysis timestamp.

### Outcome
Deterministic realized result of an operation or evaluation window.

### MarketRegime
Reproducible deterministic/statistical classification of the market environment.

### Learning
Reusable pattern or hypothesis supported by accumulated observations, outcomes, statistics, provenance and confidence.

### LearningLifecycle
Controls the evolution of a Learning as new evidence arrives.

Conceptual states:

```text
CANDIDATE
→ VALIDATING
→ ACTIVE
→ STRENGTHENING / WEAKENING
→ DRIFT_DETECTED / UNDER_REVIEW
→ SUPERSEDED / ARCHIVED
```

### ExperienceRetrievalResult
Bounded set of prior operations, learnings, events and relationships selected for a new analysis.

These concepts are architecture-level contracts. Detailed implementation schemas will be defined after the architecture revision is approved.

## Memory architecture

Continuous learning will use the same three-backend hybrid-memory direction adopted by João Resolve: SQLite/Parquet + Qdrant + Neo4j, with distinct responsibilities.

### SQLite / Parquet

Authoritative structured/numerical storage for:

- transactions;
- operations;
- feature snapshots;
- outcomes;
- market regimes;
- numerical statistics;
- learning status/version;
- audit/provenance.

### Qdrant

The target V4.0 semantic-memory standard is:

```text
Model: sentence-transformers/paraphrase-multilingual-mpnet-base-v2
Dimension: 768
B3 collection: b3_memory_768
Distance: cosine
```

This replaces the previous 384-dimensional embedding direction for new V4.0 semantic-memory data.

Semantic retrieval layer for:

- learnings;
- insights;
- research;
- event evidence;
- historical rationale;
- semantically similar prior situations.

Qdrant is a retrieval mechanism, not the numerical source of truth.

### Neo4j

Persistent relationship memory for entities and relations such as:

```text
Operation → HAS_OUTCOME → Outcome
Operation → OCCURRED_IN → MarketRegime
Operation → USES → Strategy
Learning → SUPPORTED_BY → Operation
Learning → CONTRADICTED_BY → Evidence / Operation
Learning → VALID_IN → MarketRegime
Learning → ASSOCIATED_WITH → Factor
Learning → SUPERSEDES → Learning
Instrument → EXPOSED_TO → Factor / Commodity
MarketEvent → IMPACTS → Instrument / Sector
```

The current backend-neutral Knowledge Graph contracts will be preserved and evolved toward a concrete Neo4j persistence adapter.

### Human-readable presentation

Obsidian is not part of the target V4.0 runtime memory architecture.

Human-readable learnings, theses, decisions, rationale and research summaries are generated from canonical structured memory, Qdrant retrieval and Neo4j relationships and presented through Dashboard/Copilot surfaces.

Existing Obsidian integration may remain temporarily as legacy compatibility during migration, but new V4.0 capabilities must not depend on it. Project documentation remains in Git/GitHub.

## LangGraph changes

Two explicit hooks become architecture invariants.

### PRE-ANALYSIS

Before specialist reasoning:

```text
Current deterministic context
        ↓
Feature Snapshot / Market Regime
        ↓
Experience Retrieval
        ↓
Relevant Learnings / Historical Precedents
        ↓
Specialist Agents / Synthesis / Reasoning
```

This prevents the system from reinventing previously validated knowledge.

### POST-OUTCOME

When an operation outcome becomes known:

```text
Outcome
  ↓
Experience Assembly
  ↓
Learning Candidate
  ↓
Statistical Validation
  ↓
Confidence / Aging / Drift Update
  ↓
Learning Memory Persistence
```

This path may run asynchronously and must not require a user conversation.

## Statistical validation boundary

LLMs may:

- propose candidate factors;
- identify possible patterns;
- formulate hypotheses;
- interpret evidence;
- explain learnings;
- identify contradictions.

LLMs may not independently:

- alter deterministic P&L;
- invent outcomes;
- declare statistical significance;
- promote a Learning to ACTIVE without validation policy;
- discard contradicting evidence;
- bypass point-in-time controls.

Measurable claims must be validated by deterministic/statistical methods.

The architecture must support, progressively:

- rolling windows;
- recency weighting;
- conditional probabilities;
- correlation;
- regression where justified;
- effect size;
- sample-size awareness;
- walk-forward / out-of-sample validation;
- multiple-testing safeguards;
- drift detection;
- regime-aware comparison.

## Aging and concept drift

The architecture distinguishes:

```text
Information freshness
≠
Learning validity / confidence
```

The existing Information Lifecycle Engine remains responsible for information freshness and retention.

A separate Learning Confidence / Drift responsibility will assess whether a learned relationship remains useful.

Learning relevance may consider:

```text
recency
× regime similarity
× feature similarity
× evidence quality
× sample confidence
```

The exact formula and weights are not fixed by this ADR.

Old learnings are not silently deleted. They may become WEAKENING, SUPERSEDED or ARCHIVED while remaining available for audit and historical explanation.

## Preserved architecture invariants

This ADR does not change the following V3.1 principles:

- clients use the B3 Orchestrator boundary;
- LangGraph remains the workflow authority;
- deterministic engines remain authoritative for calculations;
- MCP remains a controlled tool/service boundary;
- point-in-time correctness remains mandatory;
- Risk Validation remains downstream of reasoning/proposals;
- the human remains the final decision authority;
- autonomous broker/order execution remains prohibited;
- Dashboard/Copilot remain presentation/client surfaces;
- LLMs do not replace deterministic mathematics.

## Consequences

### Positive

- Real operations become reusable experience.
- Historical context can be reused instead of recomputed from zero.
- Learnings can strengthen, weaken or be superseded as market behavior changes.
- Recency and market-regime similarity can coexist.
- Qdrant, Neo4j and structured storage gain explicit business roles justified by approved use cases.
- The Dashboard can explain why a pattern is considered relevant and which operations support it.
- Learning remains auditable and point-in-time correct.

### Costs / complexity

- Additional canonical contracts are required.
- Historical market/context data must be sufficient to reconstruct operations.
- Statistical validation and drift logic add implementation complexity.
- Neo4j persistence becomes a justified infrastructure dependency for the target architecture.
- New observability is required for learning quality, drift and retrieval quality.
- Data quality gaps may limit some learnings and must remain explicit.

## Rejected alternatives

### 1. Pure deterministic reporting only

Rejected because it does not satisfy the approved Continuous Learning and Historical Similarity use cases.

### 2. Pure RAG / vector memory

Rejected because semantic similarity alone cannot reliably represent numerical outcomes, temporal validity, market regimes, confidence or relationship structure.

### 3. LLM-only learning

Rejected because it would make measurable financial patterns non-reproducible and insufficiently auditable.

### 4. Sliding-window-only memory

Rejected because recent data matters, but older observations from a highly similar market regime may remain relevant.

### 5. Delete old learnings when they stop working

Rejected because historical evolution, contradiction and supersession are themselves valuable knowledge.

## Compatibility

The decision is compatible with the existing repository foundations:

- current Orchestrator contracts remain valid;
- current LangGraph is extended rather than replaced;
- current Qdrant adapter is reused;
- current KnowledgeContext is reused and expanded;
- current Knowledge Graph contracts are reused;
- current lifecycle/freshness mechanisms are reused where appropriate;
- current deterministic portfolio/options/quant engines remain authoritative.

## Required next step

After acceptance of this ADR:

1. draft the next B3 Architecture revision with Continuous Learning & Experience Memory incorporated directly into the architecture;
2. include the seven canonical concepts in that architecture;
3. define the PRE-ANALYSIS and POST-OUTCOME workflows;
4. define the target persistence topology for SQLite/Parquet, Qdrant and Neo4j;
5. map current implementation status as EXISTS / PARTIAL / MISSING;
6. produce the V3.1 → next-version migration plan.

## References

- `docs/USE_CASES_INVESTMENT_OPTIONS_V2.0.md`
- `docs/USE_CASE_ARCHITECTURE_TRACEABILITY_V2.0.md`
- `docs/CANONICAL_LEARNING_DOMAIN_CONCEPTS_V0.1.md`
- `docs/ADR/0018-knowledge-context-contract.md`
- `docs/ADR/0011-data-retention-information-lifecycle.md`
- `docs/ADR/0016-qdrant-vector-store-adapter.md`
- `docs/ADR/0017-rag-ingestion-retrieval-pit.md`
