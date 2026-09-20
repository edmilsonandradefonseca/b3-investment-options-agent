# B3 Investment & Options Agent — Current Status

## Current focus

Dashboard documentation, validation and incremental completion of the React Dashboard.

## Repository

- GitHub: `edmilsonandradefonseca/b3-investment-options-agent`
- Active development branch: `feature/mcp-mvp`
- Pull request: #6 — Dashboard gate: React + Orchestrator + BTG E2E
- Software source of truth: GitHub repository
- Current development head: `e494658`

## Dashboard status

| Module | Status |
|---|---|
| Portfolio | IMPLEMENTED / manually validated / E2E |
| Options Intelligence | IMPLEMENTED / manually validated / E2E |
| Portfolio Intelligence | IMPLEMENTED / manually validated / E2E |
| Opportunities | IMPLEMENTED against OpportunitySet contract / E2E |
| Copilot | IMPLEMENTED; Golden Cases C01–C08 covered by automated UI/contract tests |
| Knowledge | Backend indicators only; UI not implemented |
| Reconciliation | Backend engine available; UI not implemented |

## Data ingestion status

| Source | Status |
|---|---|
| BTG portfolio Excel | VALIDATED active snapshot |
| Options transactions Excel | VALIDATED loader/snapshot flow |
| Brokerage notes PDF | PROCESSED into SQLite option ledger + source manifest; multiple-file upload supported |

Brokerage notes are now parsed and persisted. Runtime reconciliation now loads the SQLite ledger alongside the active options Excel snapshot, exposes auditable cross-source match statuses, and keeps the brokerage ledger out of the existing P&L input path to avoid double counting.

## Dashboard ↔ Orchestrator

The React Dashboard uses FastAPI `POST /orchestrate` for analytical snapshots and Copilot requests.

Dashboard views include:
- `portfolio`
- `options`
- `portfolio-intelligence`

The Copilot sends `surface=copilot` and a Golden Case `use_case_id`.

Upload endpoints:
- `POST /imports/portfolio`
- `POST /imports/options`
- `POST /imports/brokerage-notes`

## Verified automated gate

Commit `8634847`:
- CI #606: SUCCESS
- Dashboard + Copilot Gate #91: SUCCESS

The gate covers backend contracts/deep tests, React build and Playwright E2E.

## Implemented governance relevant to the Dashboard

- Available-capital constraint for opportunities.
- Evidence reference/quality validation.
- Evidence temporal coherence.
- Evidence source coherence.
- Deterministic portfolio capital constraint.
- Golden Cases C01–C08.
- Brokerage ledger idempotency and source manifest.

## Phase 3 — Runtime integration

Implemented in commits `57a571c` and `e5882d8` with runtime tests in `b7fe968`.

- `options_reconciliation` is now part of the orchestrator state and Dashboard snapshot.
- Runtime loads persisted brokerage transactions from `data/options.sqlite3`.
- Source-manifest coverage is propagated into reconciliation evidence.
- Excel and brokerage transactions remain separate inputs; brokerage transactions are not added to `OptionPerformanceEngine`.
- Existing P&L calculation therefore remains protected from cross-source double counting.

## Phase 4 — Reconciliation UI

Implemented in commits `b1adab9`, `c5bc67b` and E2E coverage in `629d86d`.

- Added a dedicated Reconciliation navigation view.
- UI consumes `dashboard_snapshot.options_reconciliation` from the Orchestrator.
- Shows match statuses, history coverage, source coverage and review warnings.
- React contains presentation only; reconciliation logic remains in Python.
- Added Playwright coverage for the structured reconciliation response.

## Phase 5 — Opportunities UI

Implemented the Opportunities Dashboard view against the existing `OpportunitySet` / `OpportunityIntelligence` contract.

- Added `opportunity_set` to the Dashboard snapshot contract.
- React presents eligible opportunities, action candidates, rejected opportunities, quality and provenance metadata.
- No ranking, valuation, capital or risk logic was duplicated in TypeScript.
- Playwright covers the empty OpportunitySet contract path.
- The current Dashboard runtime does not fabricate opportunities when upstream market inputs are unavailable; production population of `OpportunitySet` remains the next backend integration step.
## Phase 6 — Copilot Golden Cases

Implemented and validated the eight Golden Cases through the real LangGraph workflow in commit `590a445` and cleanup/docs commits `06abb4c` and `c528d79`.

- C01–C08 are parameterized as scenario-specific workflow tests.
- The test exercises the real LangGraph graph, deterministic context propagation, capital governance, synthesis boundary, decision schema and `RiskValidator`.
- C02 verifies the authoritative capital constraint moves an unaffordable opportunity to `rejected_opportunities` with the explicit capital reason.
- C08 verifies missing evidence is rejected by the real risk validator.
- Deterministic doubles are used for specialist/knowledge/reasoning components so CI is reproducible and does not require external LLM credentials.
- CI #660: SUCCESS.
- Dashboard + Copilot Gate #145: SUCCESS.

This closes the workflow-integration portion of Phase 6. It does not claim production acceptance with an external LLM; that remains a separate validation layer.

## Phase 7 — Knowledge UI

Implemented the first read-only Knowledge workspace.

- Added POST /knowledge/query as a bounded server-side retrieval contract.
- Query execution uses ObsidianRetriever + InMemoryKnowledgeGraphStore + KnowledgeIndexer + KnowledgeContextBuilder.
- The UI presents RAG evidence, graph entities, relations and provenance metadata.
- Added backend contract coverage with a temporary Obsidian fixture and Playwright UI contract coverage.
- No LLM reasoning is invoked by the Knowledge view.
- No Qdrant/Neo4j installation is required; vector/graph persistence remains behind the existing provider-independent contracts.

## Current next steps

1. Validate the Reconciliation Dashboard view in CI and manually.
2. Integrate production generation/population of OpportunitySet into the Dashboard deterministic snapshot when authoritative market inputs are available.
3. **Phase 6 complete:** C01–C08 now execute through the real LangGraph workflow in deterministic CI; the React E2E remains the UI boundary test.
5. Implement/validate the Knowledge view when the underlying knowledge layer is ready.
6. Keep documentation synchronized with code and tests.

## Deliberately not being advanced now

- Installing a vector database solely for the Dashboard.
- Installing Neo4j solely for the Dashboard.
- Re-opening the existing Dashboard/Orchestrator contract without a demonstrated need.
- Autonomous order execution.

## Working rule

For each Dashboard change:

**Implement → Test → Validate → Document/Fix → Next change**

See `docs/dashboard/README.md` as the canonical Dashboard entry point.
