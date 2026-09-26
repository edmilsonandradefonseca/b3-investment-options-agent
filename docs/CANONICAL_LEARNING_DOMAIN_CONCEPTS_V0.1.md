# B3 Investment & Options Agent
# Canonical Learning-Domain Concepts V0.1

**Status:** INCORPORATED INTO ARCHITECTURE V4.0 — REFERENCE  
**Date:** 2026-09-26  
**Purpose:** freeze the minimum conceptual contracts required by the approved Use Cases V2.0 before drafting the next architecture revision.  
**Current architecture:** V3.1 remains frozen until explicitly superseded.

---

## 1. Design goal

The next B3 architecture must support continuous learning from real operations without replacing deterministic analytics.

The required closed loop is:

```text
Current State
    ↓
Prior Experience Retrieval
    ↓
Analysis / Opportunity / Decision
    ↓
Operation
    ↓
Outcome
    ↓
Experience
    ↓
Learning
    ↓
Validation / Aging / Drift
    ↓
Hybrid Memory
    ↓
Next Analysis
    ↺
```

The seven canonical concepts below are the minimum domain vocabulary needed to support this loop.

---

# 2. Contract 1 — Operation

## Definition

An **Operation** represents one economic investment/options operation as experienced by the investor.

It is not the same thing as a broker transaction row.

One Operation may be composed of multiple source transactions.

Examples:

- opening and later closing a short PUT;
- a covered CALL opened and later assigned;
- a roll represented by closing one option and opening another;
- stock accumulation over multiple fills.

## Conceptual fields

```text
Operation
├── operation_id
├── strategy_type
├── underlying_id
├── instrument_ids
├── option_leg_ids
├── opened_at
├── closed_at
├── status
├── direction
├── quantity
├── capital_committed
├── source_transaction_ids
├── broker_refs
├── entry_snapshot_id
├── exit_snapshot_id
├── outcome_id
├── source_refs
└── provenance
```

## Suggested status

```text
OPEN
CLOSED
ASSIGNED
EXERCISED
ROLLED
CANCELLED
UNKNOWN
```

## Important rules

1. `Operation` aggregates broker rows into an economic event.
2. It must preserve all source transaction references.
3. It must be reconstructable deterministically.
4. It must never silently rewrite historical transactions.
5. Roll operations should preserve links to predecessor/successor operations.
6. The model must support stock and option strategies without becoming option-specific.

## Current reusable foundation

`OptionTransaction` already exists and explicitly models historical broker transaction records.

Therefore:

```text
OptionTransaction
        ↓
Operation Reconstruction
        ↓
Operation
```

---

# 3. Contract 2 — FeatureSnapshot

## Definition

A **FeatureSnapshot** is an immutable point-in-time representation of the relevant state of the world at a specific timestamp.

Its purpose is to answer:

> What information was actually available when the operation/analysis occurred?

## Conceptual fields

```text
FeatureSnapshot
├── snapshot_id
├── subject_id
├── operation_id
├── as_of
├── available_at
├── market_features
├── option_features
├── portfolio_features
├── macro_features
├── flow_features
├── commodity_features
├── event_refs
├── regime_id
├── quality_status
├── source_refs
├── provenance
└── schema_version
```

## Example market features

- underlying price;
- return_1d / 5d / 20d;
- realized volatility;
- moving averages;
- RSI;
- MACD;
- drawdown;
- beta;
- correlation;
- liquidity.

## Example option features

- strike;
- moneyness;
- DTE;
- premium;
- IV;
- delta;
- gamma;
- theta;
- vega;
- spread/liquidity.

## Example contextual features

- IBOV state;
- foreign flow;
- USD/BRL;
- SELIC;
- DI curve;
- Brent;
- iron ore;
- sector factors;
- relevant events/news.

## Rules

1. Immutable after creation except for explicit correction/versioning.
2. Must respect point-in-time availability.
3. No future information may enter an earlier snapshot.
4. Missing values remain missing; they are not backfilled with later-known facts.
5. Source timestamps and quality must be preserved.
6. Feature definitions must be versioned so historical calculations remain reproducible.

## Current reusable foundation

The existing B3 contracts already preserve:

- `observation_timestamp`;
- `available_timestamp`;
- `as_of`;
- provenance;
- quality status.

`quant_engine.py` already produces several of the numerical features required by FeatureSnapshot.

---

# 4. Contract 3 — Outcome

## Definition

An **Outcome** represents what objectively happened after an operation or decision window became observable.

This is the feedback signal for learning.

## Conceptual fields

```text
Outcome
├── outcome_id
├── operation_id
├── finalized_at
├── realized_pnl
├── realized_return
├── holding_period_days
├── max_adverse_excursion
├── max_favorable_excursion
├── assigned
├── exercised
├── exit_reason
├── capital_used
├── fees
├── taxes_if_available
├── benchmark_return
├── quality_status
├── source_refs
└── provenance
```

## Rules

1. Outcome is factual/deterministic, not LLM-generated.
2. It is finalized only when enough information exists.
3. Provisional outcomes may exist but must be marked as such.
4. Outcome calculations must be reproducible from source transactions/market data.
5. Outcome may be re-versioned if upstream broker data is corrected, never silently overwritten.

## Architectural role

```text
Operation + FeatureSnapshot
          ↓
       Outcome
          ↓
      Experience
```

---

# 5. Contract 4 — MarketRegime

## Definition

A **MarketRegime** is a reproducible classification of the market environment derived from deterministic/statistical features.

It provides context for comparing historical experiences.

## Conceptual fields

```text
MarketRegime
├── regime_id
├── as_of
├── regime_type
├── feature_snapshot_id
├── classifier_version
├── confidence
├── component_scores
├── valid_from
├── valid_to
├── source_refs
└── provenance
```

## Candidate regime dimensions

Regime classification may include independent dimensions such as:

```text
trend:
  BULL / SIDEWAYS / BEAR

volatility:
  LOW / NORMAL / HIGH / STRESS

liquidity / risk appetite:
  RISK_ON / NEUTRAL / RISK_OFF

rates:
  FALLING / STABLE / RISING

foreign flow:
  POSITIVE / NEUTRAL / NEGATIVE

commodity context:
  UP / FLAT / DOWN
```

A regime does not need to be a single monolithic label.

Example:

```text
SIDEWAYS
+ HIGH_IV
+ POSITIVE_FOREIGN_FLOW
+ HIGH_RATES
```

## Rules

1. Must be reproducible from source features and classifier version.
2. Prefer deterministic/statistical classification before LLM interpretation.
3. Older learnings may regain relevance if the same regime reappears.
4. Regime similarity and recency are separate concepts.
5. Regime changes must be historically reconstructable.

---

# 6. Contract 5 — Learning

## Definition

A **Learning** is a reusable, persistent statement supported by accumulated observations, outcomes and evidence.

A Learning is not just an Insight.

```text
Insight
= observation / interpretation / assessment

Learning
= reusable pattern or hypothesis with evidence,
  statistics, confidence, temporal validity and lifecycle
```

## Conceptual fields

```text
Learning
├── learning_id
├── subject_ids
├── strategy_type
├── statement
├── hypothesis
├── conditions
├── regime_ids
├── supporting_operation_ids
├── contradicting_operation_ids
├── supporting_evidence_refs
├── sample_size
├── recent_sample_size
├── win_rate
├── expected_return
├── effect_size
├── confidence
├── recent_confidence
├── long_term_confidence
├── first_observed_at
├── last_confirmed_at
├── valid_from
├── valid_to
├── status
├── supersedes
├── superseded_by
├── model_version
├── statistical_method
├── source_refs
└── provenance
```

Not every Learning will populate every statistical field.

## Example

```text
Learning:
Short PUT PETR4 historically performed better when:
- IBOV regime = sideways
- foreign flow = positive
- IV/RV > 1.2
- strike distance between 7% and 12%
- DTE between 25 and 40 days

N = 24
Recent N = 8
Long-term win rate = 79%
Recent win rate = 87%
Confidence = MEDIUM
Status = ACTIVE
```

## Rules

1. A Learning may begin as an agent-generated hypothesis but must not become ACTIVE solely because an LLM proposed it.
2. Measurable claims require deterministic/statistical validation.
3. Supporting and contradicting evidence must both be preserved.
4. Historical Learnings are versioned, not silently deleted.
5. Learning confidence must be recalculated as new outcomes arrive.
6. Correlation/association must not be represented as causation without appropriate evidence.
7. Learning must preserve the statistical method/version used to derive it.
8. A Learning can apply to one asset, multiple assets, a strategy, sector, portfolio or regime.

---

# 7. Contract 6 — LearningLifecycle

## Definition

**LearningLifecycle** defines how a Learning evolves as new evidence and outcomes arrive.

## Approved conceptual states

```text
CANDIDATE
     ↓
VALIDATING
     ↓
ACTIVE
     │
     ├── STRENGTHENING
     ├── WEAKENING
     └── DRIFT_DETECTED
                ↓
          UNDER_REVIEW
                ↓
        ACTIVE / SUPERSEDED / ARCHIVED
```

## State meaning

### CANDIDATE
A possible pattern has been identified.

### VALIDATING
The system is collecting/testing evidence.

### ACTIVE
The pattern has enough support to be used as contextual decision evidence.

### STRENGTHENING
Recent evidence is reinforcing the pattern.

### WEAKENING
Recent evidence is reducing confidence but has not invalidated the learning.

### DRIFT_DETECTED
A statistically/materially significant behavior change has been detected.

### UNDER_REVIEW
The learning requires reevaluation.

### SUPERSEDED
A newer Learning better represents the observed behavior.

### ARCHIVED
Retained for historical/audit value but not used as active decision context.

## Aging rules

Learning validity must distinguish:

```text
information freshness
≠
learning confidence
```

The current `InformationLifecycleEngine` remains responsible for evidence freshness and retention.

A future Learning Confidence/Drift Engine is responsible for:

- rolling-window performance;
- long-term performance;
- exponential recency weighting;
- regime similarity;
- confidence updates;
- contradiction rate;
- drift detection.

## Important rule

No fixed rule such as “older than 180 days = invalid” should be embedded into the domain model.

An older Learning may remain highly relevant if:

- it has strong evidence;
- it is repeatedly reconfirmed;
- the current regime resembles the regime where it was valid.

---

# 8. Contract 7 — ExperienceRetrievalResult

## Definition

An **ExperienceRetrievalResult** is the bounded, ranked collection of historical experiences and learnings supplied to a new analysis.

It is the explicit PRE-ANALYSIS memory contract.

## Conceptual fields

```text
ExperienceRetrievalResult
├── query_id
├── as_of
├── subject_ids
├── current_snapshot_id
├── current_regime_id
├── matched_operations
├── matched_learnings
├── matched_events
├── graph_relationships
├── similarity_components
├── relevance_score
├── temporal_score
├── regime_score
├── feature_similarity_score
├── semantic_score
├── confidence_score
├── source_refs
└── retrieval_metadata
```

## Conceptual retrieval pipeline

```text
Current FeatureSnapshot
       +
Current MarketRegime
       +
User/Agent Query
        ↓
Structured similarity
        +
Qdrant semantic retrieval
        +
Neo4j graph relations
        +
Temporal weighting
        ↓
Deterministic Experience Ranker
        ↓
ExperienceRetrievalResult
```

## Rules

1. Qdrant retrieves candidates; it is not the final relevance authority.
2. Structured feature similarity must be calculable outside the LLM.
3. Temporal weighting and regime similarity must be visible components.
4. Superseded/archived learnings may be retrievable for explanation/audit but should be clearly marked.
5. Retrieval must be bounded to prevent uncontrolled prompt growth.
6. Point-in-time queries must not expose evidence that was unavailable at the requested `as_of`.

---

# 9. Distinction between the seven concepts

```text
Broker transaction
      ↓
Operation
      ↓
FeatureSnapshot
      ↓
Outcome
      ↓
Experience
      ↓
Learning
      ↓
LearningLifecycle
      ↓
ExperienceRetrievalResult
      ↓
Next analysis
```

Where:

- **Operation** = what the investor actually did.
- **FeatureSnapshot** = what the world looked like at that time.
- **Outcome** = what actually happened afterward.
- **Experience** = Operation + Snapshot(s) + Outcome.
- **Learning** = reusable pattern derived from one or more Experiences.
- **LearningLifecycle** = how that Learning gains/loses validity through time.
- **ExperienceRetrievalResult** = what prior experience is brought back into a new analysis.

`Experience` itself may be implemented as an aggregate/view rather than a standalone persistence table; that is an implementation decision.

---

# 10. Persistence ownership

## SQLite / Parquet

Authoritative for:

- transactions;
- operations;
- feature snapshots;
- outcomes;
- regimes;
- numerical learning statistics;
- learning versions/status;
- audit.

## Qdrant

Target semantic-memory standard:

```text
Model: sentence-transformers/paraphrase-multilingual-mpnet-base-v2
Dimension: 768
Collection: b3_memory_768
Distance: cosine
```

The previous 384-dimensional direction is superseded for V4.0.

Optimized for semantic retrieval of:

- learnings;
- insights;
- research;
- rationale;
- event evidence.

Qdrant payloads should carry canonical IDs that point back to structured truth.

## Neo4j

Optimized for persistent relations such as:

```text
Operation → HAS_OUTCOME → Outcome
Operation → OCCURRED_IN → MarketRegime
Operation → USES → Strategy
Operation → ABOUT → Instrument

Learning → SUPPORTED_BY → Operation
Learning → CONTRADICTED_BY → Operation/Evidence
Learning → VALID_IN → MarketRegime
Learning → ABOUT → Instrument/Strategy
Learning → ASSOCIATED_WITH → Factor
Learning → SUPERSEDES → Learning

MarketEvent → IMPACTS → Instrument/Sector
Instrument → EXPOSED_TO → Commodity/Factor
```

## Human-readable presentation

Obsidian is not part of the target V4.0 runtime memory architecture.

Material Learnings, theses, decisions, rationale and research summaries are generated as human-readable views from canonical structured data, Qdrant semantic memory and Neo4j relational memory.

Existing Obsidian integration is legacy compatibility only. Project documentation remains in Git/GitHub.

---

# 11. LangGraph contract implications

## PRE-ANALYSIS hook

Before specialist reasoning:

```text
build current deterministic context
        ↓
build/retrieve current FeatureSnapshot
        ↓
classify MarketRegime
        ↓
retrieve prior Experience/Learnings
        ↓
attach ExperienceRetrievalResult to B3State
        ↓
specialist agents
```

Conceptual future B3State additions:

```text
feature_snapshot
market_regime
experience_context
active_learnings
historical_precedents
```

## POST-OUTCOME hook

When outcome becomes available:

```text
finalize Outcome
      ↓
assemble Experience
      ↓
identify Learning candidates
      ↓
statistical validation
      ↓
update Learning/Lifecycle
      ↓
persist structured + semantic + graph memory
```

This path may run asynchronously and must not require a user conversation.

---

# 12. Agent responsibility boundary

Agents may:

- propose candidate factors;
- interpret context;
- identify possible patterns;
- explain Learnings;
- identify contradictions;
- formulate hypotheses;
- synthesize rationale.

Agents may not independently:

- change P&L;
- change deterministic features;
- invent outcomes;
- declare statistical significance without the statistical engine;
- promote a Learning to ACTIVE without the required validation policy;
- overwrite contradictory evidence;
- bypass point-in-time controls.

---

# 13. Minimal statistical-learning principles

The architecture must support, even if phased later:

- rolling windows;
- recency weighting;
- conditional probabilities;
- correlation;
- regression where justified;
- effect-size reporting;
- sample-size awareness;
- out-of-sample / walk-forward validation;
- multiple-testing safeguards;
- drift detection;
- regime-aware comparison.

Machine learning models may be introduced later, but the first implementation should favor explainable statistical methods where they are sufficient.

---

# 14. Graph model extensions required

The current KG already has temporal/provenance-aware entities and relations.

The next architecture revision should add canonical equivalents of:

## Entity types

```text
OPERATION
OUTCOME
MARKET_REGIME
LEARNING
FACTOR
```

## Relation types

```text
HAS_OUTCOME
OCCURRED_IN
VALID_IN
SUPPORTS
CONTRADICTS
ASSOCIATED_WITH
EXPOSED_TO
```

Existing relations such as `SUPERSEDES`, `ABOUT`, `SUPPORTED_BY`, `IMPACTS`, `USES` and `UNDERLYING` should be reused where semantics already fit.

---

# 15. Compatibility with existing V3.1 architecture

These concepts do not require replacing:

- B3 Orchestrator Server;
- `b3_orchestrator()`;
- LangGraph;
- deterministic engines;
- MCP/tool boundaries;
- Risk Validation;
- human decision boundary;
- current Qdrant adapter;
- current Knowledge Context Builder;
- human-readable Dashboard/Copilot projection;
- existing portfolio/options engines.

They require extending the knowledge/experience and post-outcome paths.

The next architecture revision should therefore be an evolution of V3.1, not a rewrite.

---

# 16. Approval gate

The following conceptual contracts are proposed for freeze before the C7 architecture document is drafted:

1. **Operation**
2. **FeatureSnapshot**
3. **Outcome**
4. **MarketRegime**
5. **Learning**
6. **LearningLifecycle**
7. **ExperienceRetrievalResult**

These concepts are incorporated into the approved Architecture V4.0. The implementation sequence is:

```text
Architecture V4.0
      ↓
Contract implementation
      ↓
Unit / integration / golden tests
      ↓
Incremental migration
```
