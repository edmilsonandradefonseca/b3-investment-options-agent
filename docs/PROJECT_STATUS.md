# B3 Investment & Options Agent — Current Status

## Current focus

Phase 8 — Dashboard UX / Visual consolidation.

## Repository

- GitHub: `edmilsonandradefonseca/b3-investment-options-agent`
- Active development branch: `feature/mcp-mvp`
- Pull request: #6 — Dashboard gate: React + Orchestrator + BTG E2E
- Software source of truth: GitHub repository
- Last green gate head: `c761d7a`
- CI #682: SUCCESS
- Dashboard + Copilot Gate #167: SUCCESS

## Dashboard status

| Module | Status |
|---|---|
| Portfolio | IMPLEMENTED / manually validated / E2E |
| Options Intelligence | IMPLEMENTED / manually validated / E2E |
| Portfolio Intelligence | IMPLEMENTED / manually validated / E2E |
| Reconciliation | IMPLEMENTED / CI green / E2E |
| Opportunities | IMPLEMENTED against OpportunitySet contract / CI green / E2E |
| Copilot | IMPLEMENTED; C01–C08 covered by deterministic real-workflow tests plus UI boundary E2E |
| Knowledge | IMPLEMENTED / CI green / bounded endpoint + Playwright E2E |

## Data ingestion status

| Source | Status |
|---|---|
| BTG portfolio Excel | VALIDATED active snapshot |
| Options transactions Excel | VALIDATED loader/snapshot flow |
| Brokerage notes PDF | PROCESSED into SQLite option ledger + source manifest; multiple-file upload supported |

Brokerage notes are parsed and persisted. Runtime reconciliation loads the SQLite ledger alongside the active options Excel snapshot, exposes auditable cross-source match statuses, and keeps the brokerage ledger out of the existing P&L input path to avoid double counting.

## Dashboard ↔ Orchestrator

The React Dashboard uses FastAPI `POST /orchestrate` for analytical snapshots and Copilot requests.

Dashboard views include:
- `portfolio`
- `options`
- `portfolio-intelligence`
- `reconciliation`
- `opportunities`
- `knowledge`
- `copilot`

Upload endpoints:
- `POST /imports/portfolio`
- `POST /imports/options`
- `POST /imports/brokerage-notes`

## Phase 7 — Knowledge UI — FROZEN

Phase 7 is closed and frozen after automated validation.

Implemented:
- bounded `POST /knowledge/query` contract;
- deterministic Obsidian retriever;
- `KnowledgeIndexer`;
- `InMemoryKnowledgeGraphStore`;
- `KnowledgeContextBuilder`;
- read-only Knowledge Dashboard view;
- RAG evidence, graph entities, relations and provenance presentation;
- backend contract test with temporary Obsidian fixture;
- Playwright UI contract test;
- no LLM reasoning in the Knowledge view;
- Qdrant and Neo4j deliberately not required for this phase.

Validation:
- CI #682: SUCCESS
- Dashboard + Copilot Gate #167: SUCCESS
- Knowledge E2E passed in the green gate.

Freeze rule:
- Do not change Phase 7 behavior unless Phase 8 or a later backend requirement demonstrates a concrete need.
- Future vector/graph persistence must remain behind the existing provider-independent retrieval/graph contracts.

## Phase 8 — Dashboard UX / Visual — STARTED

Objective: consolidate the existing functional Dashboard into a coherent, readable and operationally clear interface **without changing analytical business rules or API contracts**.

Scope:
1. Establish a common visual hierarchy across all Dashboard views.
2. Standardize page headers, subtitles, status/quality indicators, metric cards, tables, cards and empty states.
3. Improve navigation and orientation between Portfolio, Options, Portfolio Intelligence, Reconciliation, Opportunities, Knowledge and Copilot.
4. Make data provenance, `as_of`, quality and warnings visually consistent.
5. Improve responsive behavior and information density without hiding material information.
6. Preserve React as presentation-only; no ranking, valuation, risk, capital or reconciliation logic moves into TypeScript.
7. Add visual/interaction regression coverage before declaring the phase complete.

Out of scope:
- changing the Orchestrator contract;
- changing investment/business rules;
- introducing autonomous execution;
- installing Qdrant/Neo4j;
- redesigning the deterministic engines;
- Tauri/.exe packaging.

Phase 8 working sequence:
**Audit → Design system → Implement → E2E/regression → CI → Dashboard validation → Document → Freeze**

Detailed UX contract: `docs/dashboard/ux.md`.

## Roadmap

1. Brokerage Reconciliation — FROZEN
2. No-Duplicate Tests — FROZEN
3. Runtime — FROZEN
4. Reconciliation UI — FROZEN
5. Opportunities UI — FROZEN
6. C01–C08 Real Workflow E2E — FROZEN
7. Knowledge UI — FROZEN
8. **Dashboard UX / Visual — IN PROGRESS**
9. Tauri/.exe — PENDING

## Deliberately not being advanced now

- Installing a vector database solely for the Dashboard.
- Installing Neo4j solely for the Dashboard.
- Re-opening the existing Dashboard/Orchestrator contract without a demonstrated need.
- Autonomous order execution.
- Tauri/.exe packaging before UX/visual stabilization.

## Working rule

For each Dashboard change:

**Implement → Test → CI → Validate → Document → Freeze → Next phase**
