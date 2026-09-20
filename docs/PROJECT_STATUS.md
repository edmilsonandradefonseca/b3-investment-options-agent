# B3 Investment & Options Agent — Current Status

## Current focus

Dashboard documentation, validation and incremental completion of the React Dashboard.

## Repository

- GitHub: `edmilsonandradefonseca/b3-investment-options-agent`
- Active development branch: `feature/mcp-mvp`
- Pull request: #6 — Dashboard gate: React + Orchestrator + BTG E2E
- Software source of truth: GitHub repository
- Current validated head: `8634847`

## Dashboard status

| Module | Status |
|---|---|
| Portfolio | IMPLEMENTED / manually validated / E2E |
| Options Intelligence | IMPLEMENTED / manually validated / E2E |
| Portfolio Intelligence | IMPLEMENTED / manually validated / E2E |
| Opportunities | PLACEHOLDER |
| Copilot | IMPLEMENTED; Golden Cases C01–C08 covered by automated UI/contract tests |
| Knowledge | Backend indicators only; UI not implemented |
| Reconciliation | Backend engine available; UI not implemented |

## Data ingestion status

| Source | Status |
|---|---|
| BTG portfolio Excel | VALIDATED active snapshot |
| Options transactions Excel | VALIDATED loader/snapshot flow |
| Brokerage notes PDF | PROCESSED into SQLite option ledger + source manifest; multiple-file upload supported |

Brokerage notes are now parsed and persisted. They are still a separate source from the active options Excel snapshot and must pass reconciliation before becoming part of a canonical consolidated P&L view.

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

## Current next steps

1. Integrate brokerage ledger with the reconciliation/runtime path without double counting.
2. Implement the Reconciliation Dashboard view.
3. Implement Opportunities using the existing OpportunitySet/Opportunity Intelligence.
4. Validate C01–C08 against the real workflow, not only mocked E2E responses.
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
