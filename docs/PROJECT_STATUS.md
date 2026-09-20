# B3 Investment & Options Agent — Current Status

## Current focus

Dashboard validation and incremental completion of the React Dashboard.

## Repository

- GitHub: `edmilsonandradefonseca/b3-investment-options-agent`
- Active development branch: `feature/mcp-mvp`
- Pull request: #6 — Dashboard gate: React + Orchestrator + BTG E2E
- Software source of truth: GitHub repository

## Dashboard status

| Module | Status |
|---|---|
| Portfolio | IMPLEMENTED / manually validated |
| Options Intelligence | IMPLEMENTED / manually validated |
| Portfolio Intelligence | IMPLEMENTED / manually validated |
| Opportunities | PLACEHOLDER — next implementation |
| Copilot | IMPLEMENTED; Golden Cases C01–C08 covered by automated tests |
| Knowledge | Backend indicators only; not the current dashboard focus |

## Data ingestion status

| Source | Status |
|---|---|
| BTG portfolio Excel | VALIDATED active snapshot |
| Options transactions Excel | validated loader/snapshot flow |
| Brokerage notes PDF | STAGED; multiple-file upload supported in React; ledger processing is a separate governed step |

Brokerage notes are not yet represented as processed option-ledger transactions merely because they were uploaded.

## Dashboard ↔ Orchestrator

The React Dashboard uses the FastAPI `POST /orchestrate` endpoint for dashboard snapshots and Copilot requests.

Dashboard views send `dashboard_view` values such as:
- `portfolio`
- `options`
- `portfolio-intelligence`

The Copilot sends `surface=copilot` and a Golden Case `use_case_id`.

Upload endpoints are transport/ingestion endpoints:
- `POST /imports/portfolio`
- `POST /imports/options`
- `POST /imports/brokerage-notes`

The business intelligence remains behind the orchestrator/workflow boundary.

## Implemented governance relevant to the Dashboard

- Available-capital constraint for opportunities.
- Evidence reference/quality validation.
- Evidence temporal coherence.
- Evidence source coherence.
- Deterministic portfolio capital constraint.
- Golden Cases C01–C08.

## Current next steps

1. Finish validation of multiple brokerage-note upload and confirm staged status.
2. Implement the React Opportunities view using the existing deterministic OpportunitySet; do not duplicate investment logic in React.
3. Validate C01–C08 through the real Dashboard with loaded data.
4. Record dashboard test results.
5. Expand technical/user documentation after the Dashboard stabilizes.

## Deliberately not being advanced now

- Vector database installation.
- Neo4j installation.
- Re-opening the existing Dashboard/Orchestrator contract without a demonstrated need.
- Autonomous order execution.

## Working rule

For each Dashboard change:
**Implement → Test → Validate → Freeze → Next change.**
