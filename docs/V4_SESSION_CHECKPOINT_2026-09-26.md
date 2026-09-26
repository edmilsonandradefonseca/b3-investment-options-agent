# V4 Session Checkpoint — 2026-09-26

## Purpose

This checkpoint records the exact state of the Architecture V4 hardening work at the end of the 2026-09-26 session so the next session can resume without re-discovery.

## Active branch / PR

- Branch: `docs/v4-architecture-hardening`
- Pull Request: #24 — `V4 hardening: hybrid retrieval, PIT availability, and architecture alignment`
- Base: `main`

## What was already present on main before this hardening session

Architecture V4 implementation had already progressed through Phases 1–8:

1. Canonical V4 contracts
2. Historical experience / point-in-time substrate
3. Structured learning
4. Experience retrieval
5. Memory projection / Neo4j bridge
6. LangGraph PRE-ANALYSIS and POST-OUTCOME workflows
7. Strategy comparison + scenario/stress
8. Dashboard + AnalysisRun + change detection

The main gap discovered was that some architecture/documentation language was ahead of the concrete implementation details.

## Completed in this hardening session

### 1. Documentation and architecture alignment

Updated:

- `docs/V4_IMPLEMENTATION_STATUS.md`
- `docs/ARCHITECTURE_V4.0.md`
- `docs/USE_CASE_ARCHITECTURE_TRACEABILITY_V2.0.md`
- `README.md`

Added:

- `docs/ADR/0021-hybrid-retrieval-evidence-ranking-memory-authority.md`

Key architectural decisions frozen/refined:

- SQL / Parquet is authoritative structured state.
- Qdrant is a reconstructible retrieval projection.
- Neo4j is a reconstructible relationship projection.
- Obsidian is not part of the target V4 runtime architecture.
- Hybrid retrieval is dense + sparse + filters + fusion + reranking.
- Qdrant score is not the final relevance score.
- Point-in-time reasoning must respect system availability, not only publication/event time.
- Claim / Evidence provenance is an explicit target.
- LLMs may propose/interpret; deterministic services commit state.

### 2. Dense + sparse + RRF retrieval

Implemented optional hybrid Qdrant mode in:

- `src/b3_agent/knowledge/qdrant_store.py`

Behavior:

```text
Dense semantic retrieval
+
Sparse lexical retrieval
        ↓
Qdrant-native RRF
        ↓
candidate set
```

Sparse retrieval currently uses a deterministic lexical hashing baseline intended to capture exact tokens such as:

- tickers;
- option symbols;
- strategy labels;
- named identifiers.

The store remains backward compatible:

- default = legacy dense-only collection;
- `hybrid=True` = named dense + sparse vectors.

### 3. Learning semantic index hybrid path

Updated:

- `src/b3_agent/knowledge/learning_semantic.py`

When the Qdrant store is hybrid-enabled, learning retrieval now uses dense + sparse + RRF.

### 4. Point-in-time availability hardening

Updated:

- `src/b3_agent/knowledge/retrieval_pipeline.py`

Historical retrieval now rejects evidence that had not yet been acquired by the system at the requested `as_of`.

Current approximation:

- `published_at` = publication time;
- `retrieved_at` = earliest explicit system-availability timestamp in the current EvidenceMetadata contract.

Historical replay must therefore satisfy:

```text
published_at <= as_of
retrieved_at <= as_of
valid_from <= as_of
valid_to >= as_of, when present
```

Future refinement may introduce a dedicated `available_at` field.

### 5. Explicit retrieval trace

Added contracts:

- `RetrievalTrace`
- `RetrievalTraceItem`

in:

- `src/b3_agent/schemas/experience.py`

The trace records, where available:

- fusion score;
- initial rank;
- final rank;
- semantic/fusion component;
- feature similarity;
- regime similarity;
- temporal score;
- confidence;
- lifecycle score;
- contradiction score;
- historical usefulness.

The ranker is now identified as:

```text
experience-ranker-v2
```

### 6. Retrieval trace persistence

Added SQLite table:

- `retrieval_traces`

Added repository:

- `src/b3_agent/repositories/retrieval_trace.py`

This enables later comparison of ranker versions and retrieval strategies.

### 7. Typed memory aging

Learning aging now prefers:

```text
last_confirmed_at
→ last_updated_at
→ first_observed_at
```

Learning temporal decay is configurable by `LearningScope`.

Current defaults:

- PERSONAL_EXPERIENCE: 365 days
- MARKET_OBSERVATION: 90 days
- EXTERNAL_RESEARCH: 180 days
- MODEL_DERIVED: 180 days
- COMBINED: 365 days

Experience records keep the existing configurable `half_life_days` path for backward compatibility.

### 8. Regime-aware old knowledge

Regime similarity remains a separate ranking signal from temporal decay.

This means an old learning may remain relevant when:

- the current regime matches the conditions under which the learning was observed;
- it was recently reconfirmed;
- or both.

Old knowledge is not automatically deleted merely because it is old.

### 9. Drift / contradiction handling

The ranker now distinguishes:

- confidence;
- relevance;
- lifecycle;
- contradiction;
- historical usefulness.

Rules:

```text
drift / weakening / under review
→ lower relevance
→ do not rewrite confidence

contradictory evidence
→ lowers relevance
→ does not delete the learning
```

Superseded / archived knowledge remains retrievable with lower lifecycle score for audit/history.

### 10. Historical usefulness separated from truth confidence

Added:

- `historical_usefulness_score`

It is intentionally separate from:

- `confidence_score`;
- `relevance_score`.

Default ranking weight:

```text
historical_usefulness_weight = 0.0
```

Therefore usefulness does not influence ranking until explicitly enabled/calibrated.

This avoids the incorrect rule:

```text
profitable outcome = supporting evidence was true
```

### 11. PRE-ANALYSIS workflow bug fixed

Important discovered bug:

The PRE-ANALYSIS workflow loaded `Learning` objects but did not pass them into `ExperienceRanker`.

Fixed in:

- `src/b3_agent/orchestration/experience_workflow.py`

Now the actual workflow uses:

- last confirmation;
- typed aging;
- lifecycle status;
- contradictions;
- regime matching.

The service also accepts a:

- `retrieval_trace_sink`

so retrieval traces may be persisted automatically.

## Tests added / expanded

Coverage added for:

- dense+sparse Qdrant RRF;
- point-in-time rejection of not-yet-retrieved evidence;
- retrieval trace emission;
- retrieval trace SQLite persistence;
- last-confirmation-based aging;
- scope-dependent aging;
- old learning + matching regime;
- drift reducing relevance without rewriting confidence;
- contradiction reducing relevance without deleting learning;
- historical usefulness being opt-in;
- PRE-ANALYSIS workflow applying lifecycle ranking;
- workflow trace sink.

## CI status

The last fully completed CI checked during the session passed:

```text
CI run 823
status: completed
conclusion: success
```

Note: work continued after that successful run, so the next session must check CI for the current PR head before merging.

## Work started but NOT completed

The next block was started:

### Decision → Evidence → Outcome attribution

Created:

- `src/b3_agent/schemas/usefulness.py`

Initial contracts:

- `OutcomeAssociation`
- `DecisionEvidenceOutcomeAttribution`
- `HistoricalUsefulnessAssessment`

This is only the contract start. The engine, persistence, workflow integration and tests are NOT complete yet.

The design intent is:

```text
Decision
   ↓
Evidence used
   ↓
Outcome observed
   ↓
Attribution observation
   ├── POSITIVE
   ├── NEGATIVE
   └── INCONCLUSIVE
   ↓
weighted historical usefulness
```

Important invariant:

> Association is not causation. A profitable outcome must not automatically confirm every evidence item used in the decision.

## Remaining hardening blocks

Approximately four major blocks remain before considering the current V4 hardening pass complete.

### Block 1 — Decision → Evidence → Outcome usefulness

Status: **STARTED / INCOMPLETE**

Next tasks:

1. implement attribution engine;
2. define deterministic or explicit association inputs;
3. calculate usefulness with shrinkage / low-sample protection;
4. persist attribution observations;
5. expose usefulness by canonical evidence/learning ID;
6. feed usefulness into ranker only when explicitly enabled;
7. tests proving no automatic causal attribution.

### Block 2 — Source Document → Claim → Evidence provenance

Status: **NOT STARTED**

Target:

```text
Source Document
      ↓
Claim
      ↓
Supporting / Contradicting Evidence
```

Need:

- canonical claim IDs;
- source provenance;
- claim validity/version;
- support/contradiction links;
- reasoning references to claim/evidence rather than entire documents where practical.

### Block 3 — Retrieval benchmark and metrics

Status: **NOT STARTED**

Build an evaluation corpus / benchmark for:

```text
A. dense-only
B. dense + filters
C. dense + sparse + RRF
D. RRF + contextual reranker
```

Metrics:

- Precision@K;
- Recall@K where labeled;
- MRR;
- NDCG;
- evidence utilization;
- latency;
- human usefulness.

This is the block that will tell us whether the added complexity actually improves retrieval.

### Block 4 — Final UC-01…UC-12 reconciliation + CI + merge

Status: **NOT STARTED**

Tasks:

1. inspect implemented code against all 12 approved use cases;
2. mark each UC as implemented / partial / remaining;
3. verify no V4 architecture contradiction remains;
4. full CI/regression;
5. resolve PR conflicts if any;
6. merge PR #24;
7. update `main` checkpoint/status;
8. optionally tag/freeze verified V4 hardening baseline.

## Recommended next-session order

Resume exactly in this order:

```text
1. Read this checkpoint.
2. Check PR #24 head + CI.
3. Finish Decision→Evidence→Outcome attribution engine.
4. Persist and test historical usefulness.
5. Build Claim/Evidence provenance model.
6. Build retrieval benchmark/evaluator.
7. Run final UC-01…UC-12 code reconciliation.
8. Full CI.
9. Merge PR #24.
10. Write final V4 hardening completion checkpoint.
```

## Do not redo

Do NOT restart architecture design for:

- storage ownership;
- Obsidian removal;
- dense+sparse direction;
- RRF direction;
- aging concept;
- regime-aware relevance;
- retrieval trace concept;
- drift/contradiction behavior.

Those decisions are already captured in code/docs/ADR in PR #24.

## Resume phrase

A future session can resume with:

> Read `docs/V4_SESSION_CHECKPOINT_2026-09-26.md` and PR #24, verify the current CI/head, and continue from Block 1: Decision → Evidence → Outcome usefulness.
