# B3 Investment & Options Agent — Architecture V4.0

**Version:** 4.0  
**Status:** APPROVED / FROZEN  
**Date:** 2026-09-26  
**Supersedes:** Architecture V3.1  
**Analytical baseline preserved:** V2.3 deterministic investment engine  
**Related ADR:** `ADR-0020 — Continuous Learning & Experience Memory`

---

# 1. Purpose

B3 Investment & Options Agent is a local-first, evidence-driven investment decision-support platform for Brazilian equities and options.

V4.0 evolves V3.1 from a context-aware analytical platform into a **continuous-learning investment intelligence system**.

The system must:

- preserve deterministic numerical authority;
- reconstruct historical operations with point-in-time correctness;
- understand the market regime in which an operation occurred;
- relate outcomes to market, portfolio, macro, flow, commodity and event context;
- identify reusable patterns;
- persist those learnings;
- re-use them in future analyses;
- weaken or supersede learnings when new evidence contradicts them;
- keep the human as final decision authority.

The defining V4.0 capability is:

> **Experience → Outcome → Learning → Memory → Retrieval → Better Context for the next analysis.**

V4.0 does not introduce autonomous trading.

---

# 2. Architecture principles

1. **Deterministic first.**  
   Numerical facts, P&L, risk metrics, valuations, option economics, similarity metrics and statistical tests belong to deterministic/statistical code whenever possible.

2. **Point-in-time correctness.**  
   Historical analysis must use only information available at the relevant timestamp.

3. **Evidence before conclusion.**  
   Facts, observations, hypotheses, learnings and decisions remain distinct.

4. **Learning is explicit.**  
   A reusable Learning is a first-class domain object, not merely a note or LLM summary.

5. **Memory is hybrid and minimal.**  
   Structured, semantic and relational memories have distinct responsibilities. V4.0 follows the João Resolve direction of using SQLite/Parquet + Qdrant + Neo4j as the runtime memory architecture; Obsidian is not part of the target runtime architecture.

6. **Recency matters, but regime matters too.**  
   Newer evidence receives temporal relevance, while older evidence may regain relevance when similar market regimes recur.

7. **Contradictions are preserved.**  
   Evidence against a Learning is retained and affects confidence.

8. **Historical knowledge is versioned, not silently deleted.**

9. **LLMs interpret; deterministic/statistical engines validate measurable claims.**

10. **LangGraph owns workflow.**  
    Server, MCP, Dashboard and storage layers must not become parallel orchestrators.

11. **Human decides.**  
    No autonomous broker/order execution is part of V4.0.

12. **Dashboard and Copilot present intelligence; they do not duplicate investment logic.**

---

# 3. Approved functional baseline

V4.0 is derived from the twelve approved use cases:

1. Portfolio Intelligence
2. Options Position & Lifecycle Intelligence
3. Opportunity Discovery
4. Strategy Comparison & What-if
5. Market & Regime Intelligence
6. Contextual Factor Intelligence
7. Historical Operation Reconstruction
8. Experience & Continuous Learning
9. Historical Similarity & Precedent Retrieval
10. Research, News & Event Intelligence
11. Risk, Scenario & Stress Intelligence
12. Decision Rationale & Conversational Copilot

The architecture is considered valid only if these use cases can be traced to explicit data, engine, agent, memory and workflow responsibilities.

---

# 4. High-level architecture

```text
                    EXTERNAL DATA SOURCES
     Broker Imports / Market / Options / Macro / Flow /
             FX / Commodities / News / Research
                              │
                              ▼
                    PROVIDER ADAPTERS
                              │
                              ▼
                 CANONICAL DATA CONTRACTS
                              │
                              ▼
                    PIT / QUALITY GATES
                              │
             ┌────────────────┴────────────────┐
             ▼                                 ▼
      CURRENT STATE                     HISTORICAL LEDGER
   replaceable snapshots                   append-only
             │                                 │
             └────────────────┬────────────────┘
                              ▼
                           USER
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
          Dashboard / React        External Clients
                │                 ChatGPT / CLI / API
                └───────────┬───────────┘
                            ▼
                 B3 ORCHESTRATOR SERVER
                            │
                            ▼
                     b3_orchestrator()
                            │
                            ▼
                        LANGGRAPH
                            │
      ┌─────────────────────┼─────────────────────┐
      ▼                     ▼                     ▼
Deterministic /        Domain Agents         Knowledge /
Statistical Engines                         Experience
      │                     │                     │
      └──────────────┬──────┴─────────────────────┘
                     ▼
              KNOWLEDGE CONTEXT
     deterministic + evidence + graph + experience
                     │
                     ▼
                 SYNTHESIS
                     │
                     ▼
               REASONING / LLM
                     │
                     ▼
               RISK VALIDATION
                     │
                     ▼
               HUMAN DECISION
                     │
                     ▼
           optional external action
                     │
                     ▼
             BROKER / EXTERNAL WORLD
                     │
                     ▼
             TRANSACTION INGESTION
                     │
                     ▼
                  OPERATION
                     │
                     ▼
                   OUTCOME
                     │
                     ▼
              OutcomeFinalized
                     │
                     ▼
             EXPERIENCE ENGINE
                     │
                     ▼
              LEARNING ENGINE
                     │
                     ▼
       STATISTICAL VALIDATION / DRIFT
                     │
                     ▼
              SQLite / Parquet
             CANONICAL SOURCE OF TRUTH
                     │
            MEMORY PROJECTION BRIDGE
              ┌──────┴──────┐
              ▼             ▼
           Qdrant          Neo4j
              └──────┬──────┘
                     ▼
               NEXT ANALYSIS
```

---

# 5. Architectural layers

## 5.0 Data source, adapter and persistence-semantics layer

V4.0 separates external acquisition from canonical domain data.

```text
External Provider / Broker File
        ↓
Provider Adapter
        ↓
Canonical Contract
        ↓
PIT + Quality Validation
        ↓
Repository / Structured Persistence
```

Provider families include:

- broker imports;
- market-price providers;
- option-chain/quote providers;
- macro/rate providers;
- foreign-flow providers;
- FX providers;
- commodity providers;
- news/research providers.

Provider-specific schemas must not leak into agents, LangGraph or Dashboard logic.

### Current State vs Historical Ledger

V4.0 explicitly separates two persistence semantics:

```text
CURRENT STATE
Portfolio / option snapshot
→ replaceable
→ latest validated state

HISTORICAL EXPERIENCE
Transactions / Operations / Outcomes
→ append-only / versioned
→ never replaced by a new current-state snapshot
```

The current BTG/Excel snapshot replacement rule remains valid for current-state ingestion and does not apply to the historical operation ledger.

Historical source corrections create explicit corrected/versioned records and audit links; they do not silently rewrite learning evidence.

## 5.1 Client layer

Clients include:

- React/Tauri Dashboard;
- conversational Copilot;
- external ChatGPT;
- CLI/API;
- future authorized clients.

Clients may:

- submit requests;
- upload validated source files;
- display structured results;
- display rationale/evidence;
- request comparisons or historical precedent.

Clients must not:

- access SQLite/Parquet directly;
- access Qdrant directly;
- access Neo4j directly;
- call provider adapters directly;
- perform valuation/ranking/risk calculations;
- orchestrate agents.

---

## 5.2 B3 Orchestrator Server

The Orchestrator Server remains the application boundary.

Responsibilities:

- authentication/authorization where applicable;
- request validation;
- configuration/runtime;
- session/context handling;
- logging/audit;
- invocation of `b3_orchestrator()`;
- structured response serialization.

It must remain thin.

It must not contain:

- portfolio strategy;
- valuation;
- options logic;
- statistical learning;
- agent sequencing;
- risk bypasses.

---

## 5.3 LangGraph

LangGraph remains the single workflow authority.

V4.0 introduces two explicit workflow invariants:

### PRE-ANALYSIS retrieval

```text
Request
  ↓
Deterministic Context
  ↓
Current Feature Snapshot
  ↓
Current Market Regime
  ↓
Prior Experience Retrieval
  ↓
ExperienceAssessment
  ↓
Knowledge Context
  ↓
Specialist Agents
```

### POST-OUTCOME learning

```text
Transaction/Reconciliation update
   ↓
Operation Finalized
   ↓
Outcome Engine
   ↓
OutcomeFinalized domain event
   ↓
Experience Assembly
   ↓
Learning Candidate
   ↓
Statistical Validation
   ↓
Learning / Lifecycle Update
   ↓
Hybrid Memory Persistence
```

POST-OUTCOME may run asynchronously and does not require a user conversation. The canonical trigger is the idempotent `OutcomeFinalized` domain event emitted only after the Outcome Engine has enough validated information to finalize an operation result.

---

# 6. Deterministic and statistical intelligence layer

The deterministic/statistical layer is the numerical source of truth.

## 6.1 Portfolio Engine

Responsibilities:

- positions;
- cash;
- concentration;
- weights;
- exposure;
- assignment capital;
- covered-call coverage;
- portfolio P&L;
- portfolio-level risk inputs.

Existing V2.3/V3.1 engines are preserved and extended.

## 6.2 Options Engine

Responsibilities:

- PUT/CALL economics;
- strike/moneyness;
- premium;
- DTE;
- assignment/exercise exposure;
- covered/uncovered state;
- IV/Greeks where available;
- roll/close comparison inputs;
- option P&L.

## 6.3 Valuation Engine

Remains deterministic.

Responsibilities:

- valuation ranges;
- scenario assumptions;
- accumulation/reference levels;
- valuation evidence for opportunity analysis.

## 6.4 Quant Engine

Responsibilities:

- returns;
- volatility;
- trend;
- moving averages;
- RSI;
- MACD;
- drawdown;
- beta;
- correlation;
- liquidity;
- completeness.

V4.0 extends quant outputs into reusable FeatureSnapshots.

## 6.5 Opportunity Engine

Responsibilities:

- canonical opportunity production;
- capital feasibility;
- deterministic ranking;
- portfolio impact inputs;
- strategy alternatives.

V4.0 may use prior experience as context but must not allow the LLM to rewrite deterministic opportunity facts.

## 6.6 Strategy Comparison Engine

New V4.0 composition capability for UC-04.

It reuses Portfolio, Options, Valuation, Opportunity, Experience and Risk engines rather than duplicating them.

Canonical output:

```text
StrategyComparison
├── alternative_a
├── alternative_b
├── capital_required
├── payoff
├── valuation_context
├── liquidity
├── portfolio_impact
├── risk
├── historical_experience
├── assumptions
└── opportunity_cost
```

The comparison must preserve deterministic facts and expose historical experience separately from forward-looking assumptions.

## 6.7 Scenario / Stress Engine

New V4.0 capability.

Responsibilities:

- deterministic price/rate/FX/commodity shocks;
- option/portfolio impact;
- assignment/capital stress;
- concentration stress;
- sensitivity analysis.

Canonical contracts:

```text
ScenarioDefinition
├── scenario_id
├── shocks
├── assumptions
├── as_of
└── provenance

StressResult
├── portfolio_pnl
├── option_pnl
├── assignment_capital
├── cash_after_stress
├── concentration
├── liquidity
├── sensitivities
└── quality_status
```

The existing RiskValidator remains a downstream governance gate and is not replaced by stress testing.

---

# 7. Experience model

V4.0 introduces a canonical experience chain.

```text
Broker Transaction
       ↓
Operation
       ↓
FeatureSnapshot(s)
       ↓
Outcome
       ↓
Experience
```

## 7.1 Operation

An Operation is an economic action, not merely a broker row.

One Operation may contain multiple source transactions.

Examples:

- short PUT opened and later closed;
- short PUT assigned;
- covered CALL;
- roll;
- stock accumulation;
- stock exit.

The system must preserve source transaction provenance.

## 7.2 FeatureSnapshot

An immutable point-in-time representation of the relevant state at a specific timestamp.

Possible dimensions:

```text
Market
Options
Portfolio
Macro
Flow
FX
Commodities
Events
News references
Risk
```

Feature definitions are versioned.

## 7.3 Outcome

Represents what objectively happened.

Possible metrics:

- realized P&L;
- return;
- holding period;
- MAE;
- MFE;
- assignment;
- exercise;
- capital used;
- benchmark return;
- exit reason.

Outcome is deterministic and reproducible.

## 7.4 Experience

Experience is the aggregate:

```text
Operation
+
FeatureSnapshot(s)
+
Outcome
```

It may be implemented as a derived aggregate/view rather than a separate physical table.

## 7.5 Historical retention invariant

Raw source datasets may follow bounded retention policies, but experience-critical derived records must survive those windows.

Persistent/versioned experience records include:

- Operation;
- operation-linked FeatureSnapshot;
- Outcome;
- MarketRegime references used by an Experience;
- Learning evidence links;
- learning statistics/version history.

Therefore a 90-day raw options-data retention policy or 360-day raw stock-data retention policy must never delete the compact derived evidence required to reconstruct a Learning.

---

# 8. Market Regime Intelligence

`MarketRegime` becomes a first-class V4.0 concept.

A regime is derived from deterministic/statistical features.

Possible independent dimensions:

```text
Trend:
BULL / SIDEWAYS / BEAR

Volatility:
LOW / NORMAL / HIGH / STRESS

Risk appetite:
RISK_ON / NEUTRAL / RISK_OFF

Rates:
FALLING / STABLE / RISING

Foreign flow:
POSITIVE / NEUTRAL / NEGATIVE

Commodity:
UP / FLAT / DOWN
```

Example:

```text
SIDEWAYS
+ HIGH_VOL
+ POSITIVE_FOREIGN_FLOW
+ HIGH_RATES
```

Rules:

- reproducible from inputs;
- classifier/version preserved;
- historical regimes reconstructable;
- regime similarity distinct from recency.

---

# 9. Contextual Factor Intelligence

V4.0 must allow agents to propose candidate relationships while statistical engines evaluate them.

Examples:

For PETR4:

- Brent;
- USD/BRL;
- IBOV;
- foreign flow;
- volatility;
- dividend events;
- sector/company events.

For VALE3:

- iron ore;
- China indicators/events;
- USD/BRL;
- foreign flow;
- IBOV;
- volatility.

Pipeline:

```text
Agent proposes candidate factor
        ↓
Statistical Engine
        ↓
Association / No support / Contradiction
        ↓
Learning Candidate
```

Supported methods may include, progressively:

- conditional statistics;
- correlation;
- regression where justified;
- effect size;
- feature importance where justified;
- regime-conditioned analysis;
- walk-forward validation;
- multiple-testing safeguards.

Correlation must not be represented as causation without appropriate evidence.

---

# 10. Learning architecture

## 10.1 Insight vs Learning

```text
Insight
= observation / interpretation / assessment

Learning
= reusable pattern/hypothesis with accumulated
  evidence, statistics, confidence, temporal validity
  and lifecycle
```

An LLM may generate an Insight or Learning Candidate.

An LLM cannot alone promote a measurable claim into an ACTIVE Learning.

## 10.2 Learning

A Learning may contain:

- subject/assets;
- strategy;
- statement;
- hypothesis;
- conditions;
- applicable regimes;
- supporting operations;
- contradicting operations;
- supporting evidence;
- sample size;
- recent sample size;
- expected return;
- win rate;
- effect size;
- confidence;
- recent confidence;
- long-term confidence;
- first observed;
- last confirmed;
- valid_from / valid_to;
- statistical method;
- model/version;
- learning_scope;
- population_scope;
- selection_bias_warning where applicable;
- provenance.

Not every Learning requires every metric.

### Learning scope

Every Learning must state what population its evidence supports.

Canonical scope values:

```text
PERSONAL_EXPERIENCE
MARKET_OBSERVATION
EXTERNAL_RESEARCH
MODEL_DERIVED
COMBINED
```

A pattern learned from the investor's own selected operations must not be silently generalized into a market-wide probability. Personal-operation evidence may contain selection bias because the investor chose which setups to trade. The rationale must preserve that limitation.

## 10.3 Learning lifecycle

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

Old learnings are not silently deleted.

---

# 11. Aging, recency and concept drift

V4.0 distinguishes:

```text
Information freshness
≠
Learning validity/confidence
```

The current Information Lifecycle Engine remains responsible for information freshness and retention.

A new Learning Confidence / Drift responsibility evaluates whether a learned relationship remains useful.

Potential inputs:

- recent-window performance;
- long-term performance;
- exponential recency weighting;
- contradiction rate;
- regime similarity;
- feature similarity;
- sample confidence;
- drift detector output.

Conceptually:

```text
Historical Relevance
=
Temporal Recency
× Regime Similarity
× Feature Similarity
× Evidence Quality
× Sample Confidence
```

The exact formula is a configurable/calibrated implementation detail.

The architecture must support:

- rolling 30/90/180/365-day views;
- full historical retention;
- exponential decay;
- regime-aware relevance;
- drift detection;
- supersession.

---

# 12. Experience retrieval

Before a new analysis, the system should retrieve relevant prior experience.

```text
Current FeatureSnapshot
       +
Current MarketRegime
       +
User/Agent Query
        ↓
Structured Similarity
        +
Qdrant Semantic Retrieval
        +
Neo4j Relationship Retrieval
        +
Temporal Weighting
        ↓
Deterministic Experience Ranker
        ↓
ExperienceRetrievalResult
```

Retrieval components should expose their scores separately:

- semantic score;
- feature similarity;
- regime score;
- temporal score;
- confidence score.

Qdrant retrieves candidates; it does not determine truth or final relevance alone.

## 12.1 ExperienceAssessment

`ExperienceRetrievalResult` is transformed into a bounded `ExperienceAssessment` before it affects opportunity or strategy reasoning.

```text
ExperienceAssessment
├── historical_similarity
├── supporting_learnings
├── contradicting_learnings
├── recent_evidence
├── long_term_evidence
├── applicable_regime
├── confidence
├── limitations
└── provenance
```

The canonical deterministic opportunity score is preserved separately.

```text
Opportunity
├── deterministic_score
└── experience_assessment
```

Experience may contextualize an opportunity, but it must not silently mutate the deterministic score or ranking.

---

# 13. Knowledge and memory architecture

V4.0 formalizes three complementary runtime memories.

## 13.1 SQLite / Parquet — structured memory

Canonical source of truth for:

- transactions;
- operations;
- market data;
- macro/flow/commodity data;
- feature snapshots;
- outcomes;
- regimes;
- numerical learning statistics;
- learning lifecycle/status;
- audit.

## 13.2 Qdrant — semantic memory

V4.0 standardizes the semantic embedding architecture on:

```text
Model: sentence-transformers/paraphrase-multilingual-mpnet-base-v2
Dimension: 768
Target B3 collection: b3_memory_768
Distance: cosine
```

This supersedes the earlier 384-dimensional embedding direction for the target V4.0 runtime.

Optimized for semantic retrieval of:

- learnings;
- insights;
- research;
- event evidence;
- historical rationale;
- semantically similar situations.

All payloads should carry canonical IDs to structured truth.

Qdrant is a reconstructible projection. Semantic records must include at minimum:

- canonical_id;
- canonical_version;
- projection_version;
- idempotency_key where applicable.

A Qdrant write failure must not invalidate the canonical Learning stored in structured memory.

## 13.3 Neo4j — relational memory

Persistent Knowledge Graph.

Target entity concepts include:

- Instrument;
- Company;
- Stock;
- Option;
- Sector;
- Portfolio;
- Position;
- Strategy;
- Operation;
- Outcome;
- MarketRegime;
- Factor;
- Insight;
- Learning;
- Decision;
- MarketEvent;
- Evidence;
- Risk.

Target relations include:

```text
Option → UNDERLYING → Stock
Stock → BELONGS_TO → Sector
Operation → ABOUT → Instrument
Operation → USES → Strategy
Operation → HAS_OUTCOME → Outcome
Operation → OCCURRED_IN → MarketRegime

Learning → ABOUT → Instrument / Strategy
Learning → SUPPORTED_BY → Operation / Evidence
Learning → CONTRADICTED_BY → Operation / Evidence
Learning → VALID_IN → MarketRegime
Learning → ASSOCIATED_WITH → Factor
Learning → SUPERSEDES → Learning

MarketEvent → IMPACTS → Instrument / Sector
Instrument → EXPOSED_TO → Commodity / Factor
```

Relations should preserve provenance and temporal validity where applicable.

The current backend-neutral graph contracts remain valid and gain a concrete Neo4j persistence adapter.

Neo4j is a reconstructible relational projection of canonical domain state. A Neo4j projection failure must not invalidate an Operation, Outcome or Learning already committed to structured memory.

## 13.4 Human-readable presentation is a view, not a memory backend

V4.0 removes Obsidian from the target runtime architecture.

Human-readable learnings, theses, decisions, rationale and research summaries are rendered on demand by the Dashboard/Copilot from canonical structured data, semantic retrieval and graph context.

Existing Obsidian integration is treated as legacy compatibility during migration and must not become a required persistence dependency for new V4.0 workflows.

Project documentation remains in Git/GitHub and is separate from runtime investment memory.

## 13.5 Memory Projection Bridge and consistency

Structured memory is committed first.

```text
SQLite / Parquet canonical commit
        ↓
Memory Projection Bridge
        ├── Qdrant projection
        └── Neo4j projection
```

Projection writes must be:

- idempotent;
- retryable;
- observable;
- rebuildable from canonical structured records.

Projection status must be auditable by canonical ID/version. Partial projection failure is a degraded state, not loss of canonical truth.

---

# 14. Knowledge Context V4.0

The existing `KnowledgeContext` remains the bounded agent-facing knowledge contract.

V4.0 expands the conceptual context to include experience.

```text
KnowledgeContext V4
├── deterministic_context
├── rag_context
├── graph_context
├── market_events
├── feature_snapshot
├── market_regime
├── experience_context
│    └── ExperienceRetrievalResult
│         └── ExperienceAssessment
├── active_learnings
├── historical_precedents
├── freshness
├── confidence
├── sources
└── metadata
```

`ExperienceRetrievalResult` is not a parallel retrieval architecture; it is the canonical experience sub-contract inside `KnowledgeContext`.

The context must stay bounded.

Entire vector collections, unrestricted graph neighborhoods or unbounded structured history must never be sent to an LLM.

---

# 15. Agent architecture

Agents are specialized analytical/reasoning components.

## Market Agent

Uses deterministic market features, regime and evidence.

## Portfolio Agent

Analyzes holdings, concentration, exposure and portfolio implications.

## Options Agent

Analyzes option structures, lifecycle and alternatives.

## Research / Event Agent

Collects and structures external evidence.

## Experience Agent

Interprets similar historical operations and differences.

## Learning Agent

Proposes candidate learnings, identifies contradictions and explains learning evolution.

It does not validate numerical significance by itself.

## Risk Agent

Interprets deterministic risk/stress outputs.

## Synthesis Agent

Combines domain analyses into coherent decision-support material.

## Reasoning Agent

Produces structured rationale from bounded evidence/context.

No agent owns deterministic numerical truth.

---

# 16. LLM boundary

LLMs may:

- interpret user intent;
- summarize research;
- propose candidate factors;
- propose hypotheses;
- explain historical precedents;
- synthesize specialist analysis;
- identify conflicts/uncertainties;
- generate rationale;
- explain Learning evolution.

LLMs may not:

- invent market data;
- invent portfolio data;
- invent operations/outcomes;
- change deterministic ranking;
- alter P&L;
- silently calculate valuation instead of engines;
- declare statistical significance without validation;
- promote measurable Learnings without validation policy;
- discard contradictory evidence;
- bypass Risk Validation;
- execute trades.

---

# 17. Point-in-time and leakage protection

PIT remains a core architecture invariant.

Every historical reconstruction must distinguish:

- observation time;
- availability time;
- ingestion time;
- analysis `as_of`.

Historical FeatureSnapshot construction must use only information available by the requested `as_of`.

This applies to:

- prices;
- options;
- macro data;
- foreign flow;
- news;
- events;
- research;
- Learnings;
- graph relations.

Backtests and learning validation must not use future knowledge.

Walk-forward/progressive validation is preferred over random temporal mixing.

---

# 18. Risk architecture

V4.0 contains two distinct risk responsibilities.

## Scenario / Stress Engine

Quantifies adverse hypothetical states.

## Risk Validator

Governance gate over a proposed decision-support output.

Conceptually:

```text
Analysis / Proposal
      ↓
Scenario / Stress Context
      ↓
Risk Validation
      ↓
PASS / HUMAN_REVIEW / REJECT
      ↓
Human
```

Risk Validation remains deterministic and downstream.

---

# 19. Research, news and events

The Market Intelligence capability remains evidence-oriented.

V4.0 adds the requirement that new information be checked against existing knowledge.

```text
New Information
      ↓
Entity/Event Extraction
      ↓
Neo4j Relationship Lookup
      ↓
Affected Assets / Positions / Learnings
      ↓
Support / Contradict / Update / No Material Impact
      ↓
Evidence Persistence
```

A news summary alone is not a Learning.

## 19.1 AnalysisRun and change detection

To support questions such as “o que mudou desde ontem?” V4.0 persists a lightweight structured `AnalysisRun` record.

```text
AnalysisRun
├── analysis_id
├── as_of
├── request_scope
├── feature_snapshot_id
├── market_regime_id
├── relevant_learning_ids
├── opportunity_refs
├── risk_refs
├── rationale_ref
├── source_refs
└── quality_status
```

A deterministic Change Detection service compares compatible AnalysisRuns and exposes material changes in features, regime, opportunities, risks and Learning lifecycle.

---

# 20. Dashboard V4.0

Target Dashboard areas:

1. Overview
2. Portfolio
3. Options
4. Opportunities
5. Market Regime
6. Experience & Learning
7. Historical Similarity
8. Research / Events
9. Risk / Stress
10. Copilot

## Experience & Learning view

Should expose, where available:

- Learning statement;
- status;
- confidence;
- age;
- last confirmation;
- sample size;
- recent sample size;
- long-term performance;
- recent performance;
- supporting factors;
- contradicting factors;
- drift status;
- supporting operations/evidence;
- applicable regime;
- rationale.

The Dashboard remains read/presentation oriented and does not host learning logic.

---

# 21. João Resolve boundary

João Resolve may consume B3 capabilities through controlled APIs/MCP interfaces.

João must not directly manipulate:

- B3 SQLite;
- B3 Parquet;
- B3 Qdrant internals;
- B3 Neo4j internals;
- deterministic engines;
- LangGraph state.

Preferred boundary:

```text
João Resolve / OpenClaw
        ↓
B3 Orchestrator / B3 MCP
        ↓
B3 LangGraph / Services
```

Memory namespaces/collections remain isolated.

B3 learnings belong to the B3 domain even when surfaced to João.

---

# 22. Runtime and service topology

Target local-first topology:

```text
B3 Orchestrator Server
LangGraph Runtime
SQLite / Parquet
Qdrant
Neo4j
Dashboard
Provider Adapters
```

Qdrant and Neo4j remain infrastructure services behind service/repository boundaries.

No client or agent should depend on database-specific APIs directly.

---

# 23. Observability

V4.0 observability must include:

- Orchestrator health;
- LangGraph runs;
- provider calls and provider-family availability;
- current-snapshot vs historical-ledger ingestion;
- PIT validation failures;
- Qdrant retrieval quality;
- graph query/relation counts;
- learning candidate creation;
- learning promotion/rejection;
- confidence changes;
- drift detection;
- supersession;
- feature snapshot completeness;
- outcome finalization / OutcomeFinalized events;
- memory projection lag/failures/rebuilds;
- AnalysisRun change detection;
- retrieval latency;
- LLM cost/latency;
- risk validation;
- audit events.

Future metrics should include:

- precedent retrieval hit quality;
- learning precision;
- out-of-sample learning performance;
- stale learning rate;
- contradiction rate;
- regime transition frequency.

---

# 24. Auditability

A material analysis should be reconstructable through:

```text
Request
→ Deterministic Context
→ Feature Snapshot
→ Market Regime
→ Prior Experience Retrieval
→ Evidence
→ Specialist Analyses
→ Synthesis
→ Reasoning
→ Scenario/Risk
→ Response
```

A Learning should be reconstructable through:

```text
Learning
→ supporting operations
→ contradicting operations
→ feature snapshots
→ outcomes
→ statistical method/version
→ confidence history
→ lifecycle transitions
```

---

# 25. Security and autonomy

The system may autonomously:

- ingest data;
- calculate metrics;
- perform historical reconstruction;
- detect candidate patterns;
- run statistical validation;
- retrieve prior experience;
- update Learning confidence;
- classify drift;
- persist knowledge;
- generate analysis;
- generate rationale.

The system may not autonomously:

- place broker orders;
- move money;
- alter credentials;
- bypass human approval;
- execute irreversible financial actions.

Human decision remains mandatory.

---

# 26. Current implementation status against V4.0

| Capability | Status |
|---|---:|
| Orchestrator contracts | EXISTS |
| Orchestrator server/runtime | EXISTS |
| LangGraph workflow | EXISTS / PARTIAL for V4 |
| Portfolio deterministic engines | EXISTS |
| Options deterministic engines | EXISTS / PARTIAL |
| Quant engine | EXISTS |
| Opportunity pipeline | EXISTS |
| Strategy Comparison contract/engine | MISSING |
| Market Intelligence research | EXISTS |
| PIT semantics | EXISTS |
| Qdrant adapter | EXISTS; target V4 semantic runtime standardized on 768d |
| RAG / Knowledge Context | EXISTS / PARTIAL |
| KG contracts | EXISTS |
| Neo4j persistent adapter | MISSING |
| Information freshness/decay | EXISTS |
| Operation aggregate | MISSING |
| FeatureSnapshot | MISSING |
| Outcome | MISSING |
| MarketRegime Engine | MISSING |
| Experience Engine | MISSING |
| Learning domain model | MISSING |
| Learning Engine | MISSING |
| Learning confidence/drift | MISSING |
| Experience similarity ranker | MISSING |
| ScenarioDefinition / StressResult + Engine | MISSING |
| AnalysisRun / Change Detection | MISSING |
| Memory Projection Bridge / rebuild semantics | MISSING |
| OutcomeFinalized domain event | MISSING |
| ExperienceAssessment | MISSING |
| Experience & Learning Dashboard | MISSING |
| Conversational Copilot | PARTIAL |

---

# 27. V3.1 → V4.0 migration

V4.0 migration is incremental.

## Phase 1 — Domain contracts

Create/freeze:

- Operation;
- FeatureSnapshot;
- Outcome;
- MarketRegime;
- Learning;
- LearningLifecycle;
- ExperienceRetrievalResult;
- ExperienceAssessment;
- StrategyComparison;
- ScenarioDefinition / StressResult;
- AnalysisRun;
- OutcomeFinalized event contract.

## Phase 2 — Historical experience substrate

Implement:

- separate current replaceable snapshots from append-only historical ledger;
- operation reconstruction;
- outcome calculation;
- PIT FeatureSnapshot generation;
- persistent experience-derived snapshots;
- regime reconstruction;
- OutcomeFinalized event emission.

## Phase 3 — Structured learning

Implement:

- Experience Engine;
- initial statistical Learning Engine;
- confidence/version lifecycle;
- supporting/contradicting evidence links;
- learning_scope / population_scope / selection-bias metadata.

## Phase 4 — Hybrid experience retrieval

Integrate:

- Qdrant semantic Learning retrieval;
- structured feature similarity;
- regime similarity;
- temporal weighting;
- deterministic Experience Ranker;
- ExperienceAssessment integration into KnowledgeContext.

## Phase 5 — Neo4j persistence

Implement Memory Projection Bridge + concrete graph adapter and persist:

- operations;
- regimes;
- factors;
- learnings;
- evidence relations;
- projection idempotency/retry/rebuild status.

## Phase 6 — LangGraph V4

Add:

- PRE-ANALYSIS Experience Retrieval;
- experience-aware specialist analysis;
- POST-OUTCOME Learning workflow.

## Phase 7 — Strategy Comparison + Scenario / Stress

Add:

- StrategyComparison composition workflow;
- ScenarioDefinition / StressResult;
- quantitative stress/sensitivity workflows.

## Phase 8 — Dashboard V4

Expose:

- Market Regime;
- Experience & Learning;
- Historical Similarity;
- Risk / Stress;
- richer Copilot rationale;
- AnalysisRun change-detection view (“what changed”).

---

# 28. Explicit non-goals

V4.0 does not authorize:

- autonomous order execution;
- broker write integration;
- replacing deterministic calculations with LLMs;
- treating semantic similarity as statistical validation;
- treating correlation as causation;
- deleting contradictory evidence;
- unrestricted autonomous agent loops;
- direct client/database coupling;
- silent replacement of historical Learnings.

---

# 29. Architecture invariants

The following are frozen V4.0 invariants if this architecture is approved:

1. Clients communicate through the Orchestrator boundary.
2. LangGraph is the workflow authority.
3. Deterministic/statistical engines own measurable calculations.
4. PIT correctness is mandatory.
5. Operation, FeatureSnapshot, Outcome and Learning are distinct concepts.
6. Learning must preserve supporting and contradicting evidence.
7. Learning confidence evolves over time.
8. Recency and regime similarity are separate signals.
9. Qdrant is semantic retrieval, not truth; V4.0 standardizes B3 semantic memory on 768-dimensional multilingual embeddings.
10. Neo4j is relational memory, not workflow orchestration.
11. SQLite/Parquet are the canonical structured source of truth; Qdrant and Neo4j are rebuildable projections.
12. Current-state snapshots are replaceable; the historical operation ledger is append-only/versioned.
13. Experience-critical FeatureSnapshots, Outcomes and Learning evidence outlive raw-data retention windows.
14. Human-readable knowledge is generated as a view from canonical runtime memory; Obsidian is not a required V4.0 backend.
15. PRE-ANALYSIS experience retrieval is mandatory where relevant and is nested inside KnowledgeContext.
16. ExperienceAssessment contextualizes but does not silently rewrite deterministic opportunity ranking.
17. OutcomeFinalized is the canonical POST-OUTCOME trigger.
18. Learning scope/population limitations, including personal selection bias, are explicit.
19. Risk Validation remains downstream.
20. Human decision does not imply execution; operations are reconstructed from external/broker evidence.
21. Human remains final decision authority.
22. No autonomous trading.

---

# 30. Final use-case architecture gate

The second architecture review verified all twelve approved use cases against the V4.0 target design.

| UC | Use Case | V4.0 architectural path | Gate |
|---|---|---|---:|
| UC-01 | Portfolio Intelligence | Current State → Portfolio Engine → KnowledgeContext → Synthesis/Risk → Dashboard/Copilot | **PASS** |
| UC-02 | Options Position & Lifecycle Intelligence | Option/Broker Data → Options Engine → Operation/Outcome → Experience → Dashboard | **PASS** |
| UC-03 | Opportunity Discovery | Providers/Portfolio/Market → Opportunity Engine → ExperienceAssessment → Synthesis | **PASS** |
| UC-04 | Strategy Comparison & What-if | StrategyComparison → existing deterministic engines → experience/risk context | **PASS** |
| UC-05 | Market & Regime Intelligence | Provider Adapters → PIT → Quant/MarketRegime → KnowledgeContext | **PASS** |
| UC-06 | Contextual Factor Intelligence | Factor candidates → statistical validation → Learning Candidate → Learning Engine | **PASS** |
| UC-07 | Historical Operation Reconstruction | Historical Ledger → Operation → PIT FeatureSnapshots → Outcome | **PASS** |
| UC-08 | Experience & Continuous Learning | OutcomeFinalized → Experience → Learning → Validation/Drift → Hybrid Memory | **PASS** |
| UC-09 | Historical Similarity & Precedent Retrieval | KnowledgeContext → ExperienceRetrievalResult → ExperienceAssessment | **PASS** |
| UC-10 | Research, News & Event Intelligence | Research/Event evidence → graph relations → Learning impact + AnalysisRun change detection | **PASS** |
| UC-11 | Risk, Scenario & Stress Intelligence | ScenarioDefinition → Stress Engine → StressResult → Risk Validation | **PASS** |
| UC-12 | Decision Rationale & Conversational Copilot | KnowledgeContext + specialist outputs + AnalysisRun → Synthesis/Reasoning → Dashboard/Copilot | **PASS** |

The review also closed the previously identified cross-cutting gaps:

- current-state snapshots vs append-only historical ledger;
- persistent experience evidence beyond raw-data retention;
- human decision separated from external execution;
- experience contextualization separated from deterministic opportunity score;
- ExperienceRetrievalResult nested inside KnowledgeContext;
- SQLite/Parquet canonical truth with rebuildable Qdrant/Neo4j projections;
- OutcomeFinalized as the POST-OUTCOME trigger;
- learning scope and personal-selection-bias metadata;
- StrategyComparison;
- ScenarioDefinition / StressResult;
- AnalysisRun / Change Detection;
- explicit Provider Adapter / canonical-contract / PIT layer;
- target semantic memory standardized on multilingual 768d embeddings.

**Final gate result: PASS — no unresolved architecture contradiction remains against the approved twelve-use-case baseline.**

---

# 31. Freeze criteria

V4.0 is **APPROVED / FROZEN** because:

- the architecture review passed against UC-01 through UC-12;
- ADR-0020 is accepted;
- the canonical learning-domain concepts are incorporated into this architecture;
- no unresolved contradiction exists with preserved V3.1 boundaries;
- the migration sequence is accepted;
- implementation begins only through contract-first phases defined in the migration plan.

---

# 32. Final architecture statement

V3.1 established the integrated B3 application boundary:

```text
Clients
→ Orchestrator
→ LangGraph
→ Engines + Agents + Knowledge
→ Risk
→ Human Decision
```

V4.0 closes the missing learning loop:

```text
Analysis
→ Human Decision
→ optional external action
→ broker/transaction ingestion
→ Operation
→ Outcome
→ Experience
→ Learning
→ Hybrid Memory
→ Retrieval
→ Better Context
→ Next Analysis
```

The objective is not to make the B3 Agent “predict everything”.

The objective is to make the system **accumulate auditable experience, reuse validated knowledge, detect when prior patterns weaken, and present increasingly context-rich decision support without losing deterministic control.**
