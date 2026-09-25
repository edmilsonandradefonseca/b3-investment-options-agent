# B3 Investment & Options Agent — Development Closure Plan

**Date:** 2026-09-25  
**Target branch:** `feature/mcp-mvp`  
**Remote branch head reviewed:** `7fdbb2a7633ad3273e225aa3aa6ff1eb0a89b8c4`  
**Purpose:** define the shortest, controlled path to close the current B3 Investment & Options Agent development cycle as a stable decision-support MVP/research platform.

> This document is a closure plan, not an authorization to expand scope. The objective is to finish, integrate, validate, document and freeze what already exists before adding new capabilities.

---

# 1. Closure definition

The project is considered **development-closed for the current MVP/research scope** when a user can:

1. start the B3 runtime without manually launching multiple Python processes;
2. load/update the real portfolio and options data safely;
3. query current/historical market data through canonical adapters;
4. view portfolio, options, opportunities and intelligence in the Dashboard;
5. ask the Copilot a supported investment-analysis question;
6. execute the canonical Orchestrator/LangGraph workflow end-to-end;
7. retrieve bounded knowledge context from the B3 knowledge layer;
8. receive structured reasoning based on deterministic facts;
9. pass the result through deterministic risk validation;
10. persist the resulting insight/decision with provenance;
11. restart the host/runtime without corrupting state;
12. reproduce the main flows through automated tests and documented runbooks.

The system remains a **decision-support system**. Autonomous order execution is explicitly outside the closure scope.

---

# 2. What is already strong enough to preserve

Do not rewrite these areas merely to "finish" the project.

## Deterministic analytical substrate

Already materially implemented:

- portfolio ingestion;
- stock positions;
- options positions;
- option transaction / brokerage-note ingestion;
- option ledger;
- reconciliation backend;
- BRAPI adapter;
- OpLab adapters;
- quant features;
- stock valuation;
- PUT/CALL analysis;
- portfolio intelligence;
- opportunity production/ranking;
- deterministic risk validation;
- point-in-time/provenance foundations.

These components are the numerical source of truth and should remain outside the LLM.

## V3.1 orchestration boundary

The current branch now contains:

- `orchestration/contracts.py`;
- `orchestration/orchestrator.py`;
- `orchestration/runtime.py`;
- `orchestration/server.py`;
- `orchestration/workflow.py`;
- provider/market/opportunity context modules;
- V3.1 orchestration tests.

Therefore the old implementation-gap statement "no Orchestrator Server / no b3_orchestrator()" is no longer current.

## Knowledge layer

The latest reviewed branch includes a B3-native knowledge stack with:

- B3 memory manager;
- SQLite knowledge persistence;
- semantic retriever;
- Qdrant integration;
- Neo4j knowledge graph implementation;
- insight persistence;
- decision persistence;
- workflow integration;
- managed LLM runtime integration.

This must now be stabilized, not redesigned.

## Dashboard

The Dashboard has evolved through many versions and already contains validated portfolio/options/intelligence/Copilot flows.

The remaining work should converge to **one canonical app**, not continue producing additional parallel `app_vXX.py` versions.

---

# 3. Critical closure gaps

Only the following gaps should block MVP closure.

## P0.1 — Freeze one canonical runtime architecture

Current target:

```text
Dashboard / Client
        ↓
B3 Runtime
        ↓
B3 Orchestrator Server
        ↓
b3_orchestrator()
        ↓
LangGraph
        ↓
Deterministic Engines + Knowledge + LLM Gate
        ↓
Risk Validation
        ↓
Structured Decision
        ↓
Persistence / Memory
```

Required before closure:

- one documented startup path;
- one runtime configuration contract;
- one health/readiness contract;
- no manual multi-process startup for normal use;
- no second intelligence orchestrator inside runtime code.

**DONE gate:** reboot → runtime starts → orchestrator healthy → dashboard/Copilot works.

---

## P0.2 — Reconcile remote GitHub vs current runtime

Before any final freeze, compare:

```text
feature/mcp-mvp on GitHub
vs
/opt/b3-investment-options-agent
vs
/opt/b3-runtime
```

Known issue requiring explicit resolution:

### Embedding model/dimension

The reviewed remote commit still contains a B3 retriever using:

```text
paraphrase-multilingual-MiniLM-L12-v2
384 dimensions
collection = b3_memory
```

The current runtime direction has been evolving toward the multilingual MPNet 768d stack.

Do not close the project until one model/dimension/collection contract is frozen and all of the following agree:

- embedding service;
- retriever constant/config;
- Qdrant collection;
- tests;
- environment;
- documentation;
- migration/reindex procedure.

**Rule:** never silently query a collection with a different vector dimension.

---

## P0.3 — Finish canonical market-data persistence

The target data path remains:

```text
BRAPI / OpLab
      ↓
provider adapters
      ↓
canonical market contracts
      ↓
validation + provenance + PIT
      ↓
SQLite / Parquet
      ↓
repositories
      ↓
Orchestrator / LangGraph
```

Closure requirements:

- BRAPI real adapter validated;
- OpLab real adapter validated;
- canonical `as_of`, `retrieved_at`, provider and provenance;
- idempotent load;
- clear retention policy;
- Parquet historical storage working;
- no duplicate history after repeated ingestion;
- missing/stale provider data represented explicitly;
- one real historical read used successfully by the analytical path.

**DONE gate:** reload identical market data twice → row counts/state remain correct → historical query is reproducible.

---

## P0.4 — Finish portfolio/options source-of-truth reconciliation

The system now has multiple sources:

- BTG portfolio workbook snapshot;
- brokerage-note / options transaction ledger;
- market/provider data.

Closure requires an explicit rule for which source owns each fact.

Required:

- loading a new BTG workbook replaces the previous snapshot as intended;
- transaction ledger is not accidentally erased by portfolio refresh;
- open options from snapshot and ledger are reconciled;
- no double counting;
- assignment/expiration/exercise cases are represented;
- reconciliation result is visible to the user.

**DONE gate:** controlled real-data test with known positions reconciles to expected quantities/capital exposure.

---

## P0.5 — Converge Dashboard to one production MVP

Stop creating permanent parallel dashboard versions.

Select one canonical entry point, preferably:

```text
mvp/dashboard/app.py
```

Archive/remove experimental version files only after confirming nothing is lost.

Final Dashboard must contain:

1. Portfolio
2. Options Intelligence
3. Portfolio Intelligence
4. Opportunities
5. Reconciliation
6. Copilot
7. Runtime/Data Health

Knowledge/RAG internals do not need a complex visual explorer for MVP closure.

Required UX closure:

- consistent common visual language;
- responsive enough for intended desktop use;
- proper loading/empty/error states;
- readable tables;
- deterministic values traceable to backend;
- no duplicate business calculations in UI.

**DONE gate:** Dashboard E2E green + manual real-data walkthrough green.

---

## P0.6 — Make Opportunities fully real

README still describes **Opportunities** as a placeholder while the backend already contains opportunity producers/pipeline/golden tests.

Closure action:

- connect Dashboard Opportunities to the real opportunity pipeline;
- show stocks and options through a common canonical opportunity contract;
- display ranking rationale/components;
- preserve `as_of` and evidence/source references;
- do not let the UI invent ranking logic.

**DONE gate:** at least one real stock opportunity and one real options opportunity rendered from backend output.

---

## P0.7 — Freeze the canonical Copilot workflow

The Copilot must be a client of the same Orchestrator workflow, not a parallel reasoning implementation.

Target:

```text
User question
   ↓
OrchestratorRequest
   ↓
Context assembly
   ├─ portfolio
   ├─ market/options
   ├─ opportunities
   └─ bounded knowledge retrieval
   ↓
LangGraph
   ↓
deterministic analysis
   ↓
LLM Gate
   ↓ when justified
reasoning/synthesis
   ↓
risk validation
   ↓
OrchestratorResponse
```

Required:

- existing Golden Cases C01–C08 remain green;
- add real-runtime cases using current provider/repository stack;
- unsupported questions fail safely;
- no whole knowledge base in prompts;
- deterministic outputs are passed as facts, not recomputed by LLM;
- sources/evidence are visible in response metadata.

**DONE gate:** golden suite + selected live-provider integration cases green.

---

## P0.8 — Stabilize B3 knowledge/RAG/KG

The knowledge layer now exists, so closure requires proving it works reliably.

Minimum closure scope:

- SQLite knowledge record persists;
- embedding index persists;
- semantic retrieval returns the expected record;
- Neo4j entity/relation persists;
- decision/insight writes are idempotent or safely versioned;
- retrieval is bounded;
- provenance is preserved;
- `as_of` semantics are carried where applicable;
- runtime restart does not lose knowledge.

Do **not** expand into a sophisticated ontology before closing the MVP.

**DONE gate:** persist insight → retrieve semantically → traverse relevant graph relation → restart → retrieve again.

---

## P0.9 — Runtime/operations as a service

Since the B3 backend now lives on the Ubuntu runtime, normal operation should not require an interactive shell.

Required system services should have:

- automatic boot;
- restart-on-failure;
- explicit environment files;
- health endpoint;
- clear log access;
- graceful stop;
- no secrets in repository.

Suggested boundary:

```text
b3-runtime.service
   ↓
orchestrator / supporting B3 services
```

Qdrant/Neo4j/embedding can remain separate managed services.

**DONE gate:** host reboot validation with all required B3 services healthy and a successful orchestrator smoke request.

---

# 4. P1 — Required hardening before freeze

These are smaller than P0 but should be completed before the final release tag.

## Error taxonomy

Differentiate:

- validation error;
- stale data;
- provider unavailable;
- timeout;
- rate limit;
- missing knowledge;
- LLM unavailable;
- risk rejection;
- internal error.

Do not report all failures as generic exceptions.

## Observability

At minimum expose:

- runtime health;
- provider health;
- DB/Parquet accessibility;
- Qdrant health;
- Neo4j health;
- embedding health;
- orchestrator health;
- last successful data ingestion;
- data freshness;
- last Copilot request status.

## Audit trail

A relevant decision should be reconstructable from:

- request;
- `as_of`;
- data/provenance;
- deterministic outputs;
- knowledge context;
- LLM invocation metadata if used;
- risk result;
- final structured response/decision.

## Configuration freeze

Move behavior-changing runtime settings to explicit configuration and document defaults.

Do not hard-code credentials.

---

# 5. Testing strategy for closure

Do not try to maximize test count. Use a layered **closure gate**.

## Gate A — fast deterministic suite

Must validate:

- portfolio ingestion;
- options ingestion;
- reconciliation;
- quant;
- valuation;
- opportunities;
- risk;
- canonical contracts.

## Gate B — persistence

Validate:

- SQLite;
- Parquet;
- Qdrant;
- Neo4j;
- source manifests;
- idempotency.

## Gate C — orchestration

Validate:

- OrchestratorRequest/Response;
- context building;
- LangGraph path;
- LLM Gate;
- risk downstream;
- persistence.

## Gate D — provider integration

Small controlled tests:

- BRAPI;
- OpLab;
- embedding service;
- managed LLM runtime.

External providers should not make the entire deterministic unit suite flaky.

## Gate E — Dashboard E2E

Validate canonical screens and Copilot golden cases.

## Gate F — real-data smoke

Using a controlled real BTG snapshot / option ledger:

```text
load
→ reconcile
→ market refresh
→ opportunity
→ Copilot
→ risk
→ decision persistence
```

## Gate G — restart/recovery

```text
stop services
→ restart / reboot
→ health
→ read persisted portfolio/history/knowledge
→ run smoke query
```

All seven gates must be green for final freeze.

---

# 6. What should NOT block closure

These are valuable, but belong after the MVP/research freeze unless a concrete thesis requirement demands them.

- autonomous trading;
- broker order execution;
- complex multi-agent society;
- extra LLM agents for calculations;
- large news ingestion platform;
- sophisticated graph ontology;
- cloud deployment;
- multi-user SaaS;
- mobile app;
- full portfolio optimizer;
- high-frequency/intraday engine;
- ML/fine-tuning;
- institutional-grade backtesting framework;
- production brokerage integration.

Backtest/walk-forward can be a separate next phase after the operational MVP is frozen.

---

# 7. Recommended implementation order from now

Use this order strictly unless a blocker is discovered.

## Step 1 — State reconciliation

- pull/compare local vs remote;
- inventory local uncommitted work;
- resolve 384d vs 768d knowledge stack;
- freeze current environment contract.

**Output:** one trusted baseline commit.

## Step 2 — Market data + persistence final validation

- BRAPI;
- OpLab;
- Parquet;
- PIT/provenance;
- idempotency.

**Output:** frozen data layer.

## Step 3 — Portfolio/options reconciliation closure

- BTG snapshot replacement;
- ledger preservation;
- no double counting;
- reconciliation UI.

**Output:** one trusted portfolio/options state.

## Step 4 — Opportunities UI

- replace placeholder with real backend;
- stocks + options;
- ranking rationale.

**Output:** complete investment-intelligence surface.

## Step 5 — Canonical Dashboard freeze

- merge best current version into `app.py`;
- UX/error/loading/table pass;
- Dashboard E2E;
- stop version proliferation.

**Output:** Dashboard MVP release candidate.

## Step 6 — Knowledge + Copilot integrated E2E

- retrieval;
- graph context;
- LLM Gate;
- reasoning;
- risk;
- persisted insight/decision.

**Output:** full agentic decision-support flow.

## Step 7 — Runtime/service closure

- services;
- startup;
- health;
- recovery;
- reboot test.

**Output:** no-shell normal operation.

## Step 8 — Final regression and real-data acceptance

Run Gates A–G.

Fix only release-blocking defects.

## Step 9 — Documentation freeze

Update:

- README;
- architecture;
- runbook;
- data contract;
- provider strategy;
- Dashboard docs;
- environment example;
- thesis/research architecture summary.

Mark stale planning/gap documents as historical where appropriate.

## Step 10 — Final release freeze

Create:

```text
B3_MVP_FREEZE.md
```

Record:

- release commit;
- test results;
- real-data smoke results;
- known limitations;
- security constraints;
- non-goals;
- next-phase backlog.

Then tag the release, e.g.:

```text
b3-mvp-v1.0
```

After this point, new capabilities should begin in a new phase/branch rather than extending the closure branch indefinitely.

---

# 8. Practical closure scorecard

| Area | Current assessment | Closure action |
|---|---|---|
| Deterministic analytics | Strong | regression/freeze |
| Portfolio ingestion | Strong | real-data revalidation |
| Options ingestion | Strong | reconciliation closure |
| BRAPI / OpLab | Implemented | real runtime validation |
| Orchestrator V3.1 | Implemented foundation | E2E/freeze |
| LangGraph | Implemented | canonical workflow validation |
| Opportunities backend | Strong | connect real Dashboard |
| Dashboard | Advanced | converge to one app + final UX |
| Copilot | Advanced/golden cases | canonical runtime E2E |
| Risk | Implemented | final downstream validation |
| SQLite/Parquet | Implemented foundation | retention/idempotency gate |
| RAG/Qdrant | Implemented, evolving | dimension/model reconciliation |
| Neo4j/KG | Implemented foundation | minimal persistence/retrieval gate |
| Decision memory | Implemented foundation | restart/idempotency validation |
| Runtime operations | Partially consolidated | systemd/reboot closure |
| Backtest/walk-forward | Not closure-critical | next phase |
| Live trading | Explicitly excluded | future only |

---

# 9. Final Definition of Done

The current development cycle is DONE only when all statements below are true:

- [ ] GitHub and Ubuntu runtime are synchronized.
- [ ] Embedding model/dimension/collection are frozen and consistent.
- [ ] BRAPI and OpLab real adapters pass controlled integration tests.
- [ ] Historical market data persists and reloads idempotently.
- [ ] BTG portfolio refresh semantics are frozen.
- [ ] Option ledger + portfolio snapshot reconcile without double counting.
- [ ] Dashboard uses one canonical app.
- [ ] Opportunities screen is backed by the real opportunity engine.
- [ ] Reconciliation is visible in the Dashboard.
- [ ] Copilot routes through the canonical Orchestrator/LangGraph workflow.
- [ ] Golden Cases remain green.
- [ ] Knowledge retrieval is bounded, persistent and restart-safe.
- [ ] Neo4j/Qdrant/SQLite knowledge paths are validated.
- [ ] Risk validation cannot be bypassed by LLM output.
- [ ] Important decisions are auditable.
- [ ] Runtime health is observable.
- [ ] Normal operation requires no interactive shell startup.
- [ ] Full host reboot/recovery test passes.
- [ ] Final real-data smoke passes.
- [ ] CI is green.
- [ ] Documentation reflects actual code/runtime.
- [ ] MVP freeze record is created.
- [ ] Release tag is created.

---

# 10. After closure

Recommended next research phase:

```text
BACKTEST
→ WALK-FORWARD
→ PAPER PORTFOLIO
→ LONGITUDINAL EVALUATION
```

This next phase should evaluate whether the decision-support system actually improves consistency, traceability and decision quality over time.

It should **not** be mixed into the current closure work.

---

## Closure rule

From this point forward:

> **Finish integration before adding intelligence. Finish validation before adding features. Freeze the MVP before starting the next research phase.**
