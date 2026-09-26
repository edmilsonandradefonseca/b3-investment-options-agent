# B3 Investment & Options Agent
# Use Case → Architecture Traceability Matrix V2.0

**Version:** 2.0  
**Status:** ARCHITECTURE GATE — DRAFT FOR REVIEW  
**Date:** 2026-09-26  
**Functional baseline:** `docs/USE_CASES_INVESTMENT_OPTIONS_V2.0.md`  
**Current architecture baseline:** V3.1  
**Purpose:** map the 12 approved use cases to current capabilities and identify the minimum architectural evolution required before defining the next architecture version.

---

## 1. Status legend

- **EXISTS** — the core capability is implemented and reusable.
- **PARTIAL** — meaningful foundations exist, but the approved use case is not satisfied end-to-end.
- **MISSING** — the use case requires a capability that does not currently exist as an implemented B3 component.

This matrix evaluates the current repository against the approved functional baseline. It does not authorize implementation changes.

---

# 2. Executive result

| UC | Use Case | Current Status | Main reason |
|---|---|---:|---|
| UC-01 | Portfolio Intelligence | **PARTIAL** | Strong deterministic portfolio exposure/capital foundation exists; broader contextual/risk/learning integration is incomplete. |
| UC-02 | Options Position & Lifecycle Intelligence | **PARTIAL** | PUT/CALL analysis and option reconciliation exist; complete lifecycle, Greeks/IV history, realized outcome and roll intelligence are incomplete. |
| UC-03 | Opportunity Discovery | **PARTIAL** | Opportunity producers/ranking pipeline exist; market-regime, prior-experience and continuous-learning inputs are not integrated. |
| UC-04 | Strategy Comparison & What-if | **PARTIAL** | Deterministic option/stock economics exist; canonical scenario/comparison engine is not complete. |
| UC-05 | Market & Regime Intelligence | **PARTIAL** | Quant and live Market Intelligence exist; no first-class MarketRegime Engine/object. |
| UC-06 | Contextual Factor Intelligence | **PARTIAL** | Quant correlations, market research and KG contracts exist; no factor-discovery/statistical-validation pipeline. |
| UC-07 | Historical Operation Reconstruction | **MISSING** | Transaction history exists, but no canonical point-in-time Feature Snapshot + Outcome reconstruction pipeline. |
| UC-08 | Experience & Continuous Learning | **MISSING** | Insight/memory/lifecycle foundations exist, but no Learning object, Learning Engine, outcome feedback loop or drift engine. |
| UC-09 | Historical Similarity & Precedent Retrieval | **PARTIAL** | Qdrant/RAG/context retrieval foundations exist; no structured historical-state similarity engine or combined relevance ranker. |
| UC-10 | Research, News & Event Intelligence | **PARTIAL** | Market Intelligence web research and event-aware KG/RAG foundations exist; evidence-to-learning update loop is missing. |
| UC-11 | Risk, Scenario & Stress Intelligence | **PARTIAL** | Risk validator and capital-risk foundations exist; scenario/stress/sensitivity engine is missing. |
| UC-12 | Decision Rationale & Conversational Copilot | **PARTIAL** | Orchestrator/LangGraph/specialists/synthesis/reasoning exist; full experience-aware rationale and dashboard surface are incomplete. |

**Architecture implication:** the current B3 codebase already contains substantial deterministic, orchestration and knowledge foundations. The next architecture should extend these foundations with an explicit **Experience → Outcome → Learning → Memory → Retrieval** loop rather than replace them.

---

# 3. Current reusable foundations

The following repository areas are directly reusable for the approved use cases.

## 3.1 Deterministic portfolio and options

Existing foundations include:

- `portfolio/intelligence.py`
- `portfolio/capital.py`
- `portfolio/capital_risk.py`
- `portfolio/pnl.py`
- `portfolio/lifecycle.py`
- `portfolio/position_intelligence.py`
- `options/analysis.py`
- `options/put.py`
- `options/call.py`
- `options/reconciliation.py`
- option/portfolio repositories and schemas.

The current portfolio intelligence already calculates exposure, weights, short-option counts, assignment capital and covered-call coverage.

## 3.2 Quantitative analysis

`quant_engine.py` already provides deterministic features including:

- returns;
- realized volatility;
- moving averages;
- RSI;
- MACD;
- drawdown;
- beta;
- correlation;
- volume/liquidity;
- data completeness.

This should be extended, not replaced.

## 3.3 Market intelligence

`agents/market_intelligence.py` already provides a research boundary for:

- rates;
- inflation;
- fiscal policy;
- USD/BRL;
- oil / iron ore;
- global risk appetite;
- China;
- geopolitics;
- climate;
- regulation;
- capital flows;
- corporate events;
- sector developments.

It preserves evidence URLs/publication timing and distinguishes research from final decisions.

## 3.4 Qdrant / RAG

The target V4.0 semantic-memory standard is aligned with João Resolve:

```text
sentence-transformers/paraphrase-multilingual-mpnet-base-v2
768 dimensions
B3 collection: b3_memory_768
cosine similarity
```

The earlier 384-dimensional direction is superseded for new V4.0 embeddings.

`knowledge/qdrant_store.py` already provides a Qdrant adapter with:

- cosine retrieval;
- metadata payloads;
- ticker filters;
- topic/source filters;
- publication-time filters;
- validity metadata;
- confidence;
- retention class;
- decay profile.

This is a strong foundation for semantic experience retrieval.

## 3.5 Knowledge Graph

Current graph foundations include:

- `knowledge/graph_schema.py`
- `knowledge/graph_store.py`
- `knowledge/in_memory_graph.py`
- `knowledge/context.py`

The graph model already has:

- temporal validity;
- provenance;
- instruments;
- companies;
- stocks;
- options;
- sectors;
- portfolios;
- positions;
- strategies;
- insights;
- decisions;
- market events;
- risks;
- signals;
- evidence.

It also already contains useful relations such as:

- UNDERLYING;
- BELONGS_TO;
- HAS_POSITION;
- USES;
- ABOUT;
- SUPPORTED_BY;
- AFFECTS;
- IMPACTS;
- DERIVED_FROM;
- PRECEDES;
- SUPERSEDES.

**Gap:** persistence is still backend-neutral/in-memory; a concrete Neo4j persistence adapter is not yet present.

## 3.6 Knowledge context

`KnowledgeContextBuilder` already combines:

```text
RAG
+
Knowledge Graph
+
Deterministic Context
+
Point-in-Time filtering
```

This is directly reusable for the future PRE-ANALYSIS experience retrieval hook.

## 3.7 Information aging

`knowledge/lifecycle.py` already contains:

- retention classes;
- decay profiles;
- exponential freshness;
- half-life rules;
- purge eligibility.

Important distinction:

> The current lifecycle engine ages information for retrieval/storage management. It is not yet a learning-confidence/drift engine.

This foundation should be reused for temporal weighting, but learning confidence requires an additional contract.

## 3.8 Orchestration

The current LangGraph workflow already contains:

```text
retrieve
→ deterministic_context
→ knowledge_context
→ specialist agents
→ synthesis
→ reasoning
→ risk validation
→ optional memory persistence
```

This already resembles the desired PRE-ANALYSIS path.

The missing architectural loop is mainly:

```text
OPERATION
→ OUTCOME
→ EXPERIENCE
→ LEARNING
→ UPDATE MEMORY
```

---

# 4. Detailed traceability by use case

## UC-01 — Portfolio Intelligence

### Required data

- current BTG portfolio;
- stock/option prices;
- cash;
- transaction history;
- option obligations;
- sector/entity identity;
- current market context.

### Required deterministic engines

- Portfolio Intelligence;
- capital/exposure;
- P&L;
- concentration;
- assignment exposure;
- coverage;
- portfolio risk.

### Required agents

- Portfolio Agent;
- optional Synthesis/Copilot.

### Memory read/write

**Read**
- prior portfolio insights;
- active risk learnings;
- historical portfolio regimes.

**Write**
- validated portfolio insights;
- material changes;
- decisions/rationale when approved.

### Current state

**PARTIAL**

Strong deterministic implementation exists. Learning-aware risk/context is not yet integrated as a canonical portfolio workflow.

### Architecture action

**KEEP + EXTEND**

---

## UC-02 — Options Position & Lifecycle Intelligence

### Required data

- option transactions;
- option contracts;
- option quotes;
- underlying prices;
- IV;
- Greeks;
- DTE;
- strikes;
- portfolio coverage;
- realized exit/assignment outcome.

### Required deterministic engines

- PUT Engine;
- CALL Engine;
- option lifecycle;
- P&L;
- exercise/assignment exposure;
- roll/comparison calculations.

### Required agents

- Options Agent;
- Experience Agent for historical behavior.

### Memory read/write

**Read**
- prior strategy learnings;
- similar option setups;
- historical outcomes.

**Write**
- operation outcomes;
- strategy observations;
- validated learnings.

### Current state

**PARTIAL**

PUT/CALL analysis and reconciliation exist. Complete lifecycle/outcome semantics and learning integration are not complete.

### Architecture action

**KEEP + EXTEND**

A canonical `Operation` / `Outcome` identity is needed.

---

## UC-03 — Opportunity Discovery

### Required data

- portfolio;
- available capital;
- market data;
- option data;
- valuation;
- risk;
- market regime;
- prior experience.

### Required deterministic engines

- opportunity producers;
- ranking;
- capital feasibility;
- portfolio-impact calculations.

### Required agents

- Opportunity/Strategy reasoning;
- Market Agent;
- Options Agent;
- Portfolio Agent.

### Memory read/write

**Read**
- active learnings;
- similar historical opportunities;
- contradicted/superseded learnings.

**Write**
- opportunity insight;
- later outcome when the opportunity becomes an operation.

### Current state

**PARTIAL**

Opportunity infrastructure exists but does not yet use experience/regime as first-class inputs.

### Architecture action

**KEEP + EXTEND**

---

## UC-04 — Strategy Comparison & What-if

### Required data

- current position;
- candidate strategies;
- premiums;
- underlying;
- portfolio;
- market regime;
- historical outcomes.

### Required deterministic engines

- payoff engine;
- capital comparison;
- opportunity-cost engine;
- scenario engine;
- risk comparison.

### Required agents

- Strategy/Synthesis Agent.

### Memory read/write

**Read**
- historical outcomes by strategy/regime;
- prior comparisons.

**Write**
- decision rationale where material.

### Current state

**PARTIAL**

The system has deterministic strategy components but no canonical multi-strategy scenario/comparison engine.

### Architecture action

**CREATE comparison/scenario service over existing engines**

---

## UC-05 — Market & Regime Intelligence

### Required data

- IBOV;
- historical market prices;
- breadth where available;
- foreign flow;
- rates;
- FX;
- commodities;
- volatility;
- market events.

### Required deterministic/statistical engines

- feature engine;
- regime classifier;
- rolling statistics;
- volatility/state classifier.

### Required agents

- Market Agent;
- Market Intelligence Agent.

### Memory read/write

**Read**
- historical regimes;
- regime-associated learnings.

**Write**
- regime snapshots;
- material regime transitions.

### Current state

**PARTIAL**

Quant and live research foundations exist. `MarketRegime` is not a canonical first-class object and no Regime Engine exists.

### Architecture action

**CREATE MarketRegime contract + deterministic Regime Engine**

---

## UC-06 — Contextual Factor Intelligence

### Required data

- market;
- macro;
- foreign flow;
- FX;
- commodities;
- news/events;
- operation outcomes;
- portfolio state.

### Required deterministic/statistical engines

- correlation;
- conditional statistics;
- regression where justified;
- effect-size calculation;
- feature importance where justified;
- multiple-testing safeguards;
- temporal validation.

### Required agents

- Factor/Research Agent;
- Learning Agent.

### Memory read/write

**Read**
- existing factor relations;
- prior hypotheses;
- relevant evidence.

**Write**
- candidate relationships;
- validated associations;
- contradictions.

### Current state

**PARTIAL**

Correlation and research foundations exist, and the KG can represent relations. There is no complete factor-discovery → statistical-validation → learning pipeline.

### Architecture action

**CREATE Factor Intelligence / Statistical Learning service**

---

## UC-07 — Historical Operation Reconstruction

### Required data

- transaction ledger;
- entry/exit timestamps;
- market observations;
- option state;
- portfolio state;
- macro/flow/commodity data;
- news/events;
- final outcome.

### Required deterministic engines

- Point-in-Time Feature Snapshot Builder;
- operation reconstruction;
- outcome calculator.

### Required agents

- Experience Agent for interpretation only.

### Memory read/write

**Write**
- immutable feature snapshots;
- operation/outcome links;
- provenance.

### Current state

**MISSING**

The repository has historical option transaction contracts, but not a full point-in-time operation reconstruction model.

### Architecture action

**CREATE**

Required first-class contracts:

```text
Operation
FeatureSnapshot
Outcome
```

---

## UC-08 — Experience & Continuous Learning

### Required data

- operations;
- feature snapshots;
- outcomes;
- regimes;
- supporting/contradicting evidence.

### Required deterministic/statistical engines

- learning statistics;
- recency weighting;
- rolling windows;
- confidence update;
- drift detection;
- temporal validation;
- learning versioning.

### Required agents

- Learning Agent.

### Memory read/write

**Read**
- prior learnings;
- supporting operations;
- contradictions.

**Write**
- candidate learning;
- updated learning;
- superseding learning;
- evidence links.

### Current state

**MISSING**

The project has Insight/memory/lifecycle foundations, but not a canonical `Learning` domain object or Experience/Learning Engine.

### Architecture action

**CREATE as first-class architecture capability**

Required lifecycle:

```text
CANDIDATE
→ VALIDATING
→ ACTIVE
→ STRENGTHENING / WEAKENING
→ DRIFT_DETECTED / UNDER_REVIEW
→ SUPERSEDED / ARCHIVED
```

---

## UC-09 — Historical Similarity & Precedent Retrieval

### Required data

- current Feature Snapshot;
- historical Feature Snapshots;
- MarketRegime;
- historical outcomes;
- semantic learnings.

### Required deterministic/statistical engines

- numeric feature similarity;
- regime similarity;
- temporal decay;
- confidence/evidence weighting;
- combined relevance ranker.

### Required agents

- Experience Agent for explanation.

### Memory read/write

**Read**
- Qdrant semantic memory;
- structured feature/outcome history;
- graph relationships.

### Current state

**PARTIAL**

Qdrant and Knowledge Context retrieval exist, including temporal metadata. Structured state similarity and a deterministic combined ranker do not.

### Architecture action

**EXTEND retrieval into Experience Retrieval**

Conceptual relevance:

```text
recency
× regime similarity
× feature similarity
× evidence quality
× sample confidence
```

The exact formula remains a later calibration decision.

---

## UC-10 — Research, News & Event Intelligence

### Required data

- web/news research;
- entity identities;
- affected assets/sectors;
- current positions;
- existing theses/learnings.

### Required engines

- evidence normalization;
- entity/event linking;
- relevance;
- contradiction/support classification.

### Required agents

- Market Intelligence / News Agent;
- Learning Agent.

### Memory read/write

**Read**
- relevant active learnings;
- related entities and positions.

**Write**
- evidence;
- event relations;
- learning confirmation/contradiction candidate.

### Current state

**PARTIAL**

Live Market Intelligence and event-aware KG/RAG foundations exist. The feedback path from new evidence into existing learnings is missing.

### Architecture action

**KEEP + EXTEND**

---

## UC-11 — Risk, Scenario & Stress Intelligence

### Required data

- portfolio;
- option Greeks/sensitivities;
- market prices;
- scenarios;
- correlations;
- capital requirements.

### Required deterministic engines

- scenario shocks;
- stress testing;
- sensitivity;
- capital/assignment stress;
- portfolio impact.

### Required agents

- Risk Agent for interpretation.

### Memory read/write

**Read**
- historical stress episodes;
- prior risk learnings.

**Write**
- validated risk observations where useful.

### Current state

**PARTIAL**

A deterministic `RiskValidator` exists, but it currently validates proposal completeness/execution prohibition rather than performing quantitative stress analysis. Capital-risk foundations exist separately.

### Architecture action

**CREATE Scenario/Stress Engine; preserve RiskValidator as downstream governance gate**

---

## UC-12 — Decision Rationale & Conversational Copilot

### Required data

Outputs from UC-01 through UC-11.

### Required engines

No duplicate investment engine.

### Required agents

- intent/query interpretation;
- specialist agents;
- synthesis;
- reasoning.

### Memory read/write

**Read**
- current facts;
- relevant evidence;
- prior experience;
- graph context;
- active/superseded learnings.

**Write**
- material insight;
- decision rationale;
- audit.

### Current state

**PARTIAL**

The LangGraph workflow already retrieves bounded knowledge, calls specialist agents, synthesizes, reasons, validates and can persist memory.

The missing part is experience/learning-aware context and the corresponding Dashboard/Copilot presentation.

### Architecture action

**KEEP + EXTEND**

---

# 5. Required new canonical domain objects

The approved use cases reveal a small set of new first-class contracts.

## 5.1 Operation

Represents the economic operation, not only a broker row.

Minimum concepts:

- operation_id;
- strategy;
- underlying;
- option legs if applicable;
- opened_at;
- closed_at;
- capital committed;
- source transactions;
- status.

## 5.2 FeatureSnapshot

Immutable point-in-time context associated with an operation or analysis timestamp.

Conceptually:

```text
FeatureSnapshot
├── as_of
├── market_features
├── option_features
├── portfolio_features
├── macro_features
├── flow_features
├── commodity_features
├── event_refs
├── quality
└── provenance
```

## 5.3 Outcome

Represents what actually happened after the operation/decision.

Possible fields:

- realized P&L;
- return;
- duration;
- assignment/exercise;
- MAE;
- MFE;
- exit reason;
- finalized_at.

## 5.4 MarketRegime

Represents a deterministic/statistically derived state of the market.

It must be versioned and reproducible from source features.

## 5.5 Learning

Represents reusable experience supported by observations/outcomes.

It is distinct from `Insight`.

```text
Insight
= observation/assessment

Learning
= reusable pattern/hypothesis with accumulated evidence,
  statistics, confidence, validity and lifecycle
```

## 5.6 LearningEvidenceLink

Links a Learning to:

- supporting operations;
- contradicting operations;
- evidence;
- regime;
- related entities;
- superseded learnings.

---

# 6. Required new engines/services

The use cases imply the following missing or expanded services.

| Component | Need | Status |
|---|---|---:|
| Feature Snapshot Engine | reconstruct PIT context | **MISSING** |
| Outcome Engine | canonical realized outcome | **MISSING** |
| Market Regime Engine | classify/reconstruct regime | **MISSING** |
| Factor Intelligence / Statistical Engine | validate relationships | **MISSING** |
| Experience Engine | bind operation + features + outcome | **MISSING** |
| Learning Engine | create/update learning | **MISSING** |
| Drift/Confidence Engine | aging, drift, confidence update | **MISSING** |
| Experience Similarity Ranker | combine structured/semantic/regime/time relevance | **MISSING** |
| Scenario/Stress Engine | quantitative what-if/stress | **MISSING** |
| Qdrant semantic retrieval | retrieve semantic evidence using target 768d multilingual embeddings | **EXISTS/PARTIAL** |
| Knowledge Context Builder | bounded RAG + KG + deterministic context | **EXISTS** |
| Persistent Neo4j adapter | durable relationship memory | **MISSING** |
| Human-readable presentation | generated from canonical memory via Dashboard/Copilot | **PARTIAL** |

---

# 7. Required LangGraph evolution

The current workflow is a strong foundation:

```text
retrieve
→ deterministic_context
→ knowledge_context
→ specialist analysis
→ synthesis
→ reasoning
→ risk validation
→ persistence
```

The use cases require two additional architectural paths.

## 7.1 PRE-ANALYSIS EXPERIENCE RETRIEVAL

```text
current request/state
      ↓
current Feature Snapshot / MarketRegime
      ↓
Experience Retrieval
      ├── structured historical similarity
      ├── Qdrant semantic learnings
      ├── Neo4j related factors/entities
      └── temporal/regime filtering
      ↓
bounded prior experience
      ↓
specialist analysis
```

## 7.2 POST-OUTCOME LEARNING

```text
operation closes / outcome becomes known
      ↓
Outcome Engine
      ↓
Experience Engine
      ↓
Learning Engine
      ↓
statistical validation
      ↓
confidence / drift update
      ↓
Learning Memory Bridge
      ├── SQLite/Parquet
      ├── Qdrant
      ├── Neo4j
      └── Dashboard/Copilot projection when human-readable presentation is warranted
```

Learning should not depend on a user asking a new question.

---

# 8. Memory architecture consequences

## SQLite / Parquet

Must remain numerical/structured source of truth for:

- operations;
- transactions;
- market/macro/flow data;
- feature snapshots;
- regimes;
- outcomes;
- statistics;
- learning metrics;
- audit.

## Qdrant

Role:

> semantic candidate retrieval for evidence, analyses and learnings.

Qdrant does **not** become authoritative for P&L, statistics or learning confidence.

## Neo4j

The use cases now justify durable graph persistence.

Required additions to current graph vocabulary should include concepts equivalent to:

- LEARNING;
- OPERATION;
- OUTCOME;
- MARKET_REGIME;
- FACTOR;

and relations equivalent to:

- OCCURRED_IN;
- HAS_OUTCOME;
- SUPPORTS;
- CONTRADICTS;
- VALID_IN;
- ASSOCIATED_WITH;
- SUPERSEDES.

Exact names are contract-design decisions.

## Human-readable presentation

Obsidian is removed from the target V4.0 runtime architecture.

Human-readable learnings, decisions, theses, rationale and research summaries are generated from canonical structured memory plus Qdrant/Neo4j context and presented through Dashboard/Copilot surfaces.

Project documentation remains in Git/GitHub. Existing Obsidian integration is legacy compatibility and is not a dependency for new learning workflows.

---

# 9. Aging and drift architecture requirement

The current Information Lifecycle Engine already provides exponential freshness/retention.

The next architecture must distinguish two independent concepts:

### Information freshness

```text
How old/stale is this piece of evidence?
```

### Learning validity/confidence

```text
Does this learned relationship still perform under recent evidence
and the current market regime?
```

Therefore:

```text
InformationLifecycleEngine
≠
LearningConfidence/DriftEngine
```

They may share temporal-decay primitives but must not be the same responsibility.

---

# 10. Primary architecture gaps

The largest gaps are not basic RAG or deterministic investment analytics.

They are:

1. **Operation semantics beyond raw transactions**
2. **Point-in-time Feature Snapshots**
3. **Outcome model**
4. **Market Regime model/engine**
5. **Experience model**
6. **Learning model/lifecycle**
7. **Statistical validation of candidate patterns**
8. **Learning confidence + drift**
9. **Structured historical similarity**
10. **Persistent Neo4j backend**
11. **Quantitative scenario/stress engine**
12. **Dashboard Experience & Learning surface**

---

# 11. Architecture decision direction

The traceability analysis supports an evolution of V3.1 rather than a rewrite.

Keep:

```text
Clients
→ Orchestrator Server
→ b3_orchestrator()
→ LangGraph
→ Deterministic Engines + Agents + Knowledge
→ Risk
→ Human Decision
```

Add the missing closed learning loop:

```text
               ┌────────────────────────────┐
               │                            │
               ▼                            │
Current State / Market Regime               │
               ↓                            │
Prior Experience Retrieval                  │
               ↓                            │
Analysis / Opportunity / Decision            │
               ↓                            │
Operation                                   │
               ↓                            │
Outcome                                     │
               ↓                            │
Experience                                  │
               ↓                            │
Learning / Validation / Drift               │
               ↓                            │
Hybrid Memory                               │
               └────────────────────────────┘
```

---

# 12. Proposed next Architecture Gate

Before drafting the new Architecture document, freeze the following conceptual contracts:

1. `Operation`
2. `FeatureSnapshot`
3. `Outcome`
4. `MarketRegime`
5. `Learning`
6. `LearningLifecycle`
7. `ExperienceRetrievalResult`
8. roles of SQLite/Parquet, Qdrant and Neo4j
9. PRE-ANALYSIS retrieval hook
10. POST-OUTCOME learning hook

After these concepts are approved, produce the C7 ADR and the next architecture revision.

---

# 13. Architecture Gate Result

**Use cases:** APPROVED  
**Traceability:** COMPLETE FOR ARCHITECTURE REVIEW  
**Current architecture:** V3.1 remains frozen until superseded  
**Recommended direction:** evolve V3.1 with a first-class Experience & Continuous Learning subsystem  
**Rewrite required:** NO  
**C7 review required:** YES  

**NEXT:** review and approve the canonical learning-domain concepts before drafting the new architecture revision.
