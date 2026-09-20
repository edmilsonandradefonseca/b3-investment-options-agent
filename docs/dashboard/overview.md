# Dashboard Overview

## Purpose

The React Dashboard is the user-facing interface for the B3 Investment & Options Agent. It is a decision-support interface, not an order-execution interface.

## Current modules

### Portfolio

Displays the authoritative BTG portfolio snapshot returned through the Orchestrator. The UI exposes data quality and point-in-time information, including the loader status and `as_of`.

### Options Intelligence

Displays deterministic options transactions, lifecycles and accumulated realized P&L obtained through the Orchestrator workflow.

### Portfolio Intelligence

Displays deterministic portfolio exposures and capital-risk information obtained through the Orchestrator.

### Reconciliation

Provides an auditable Excel × brokerage-note view using the runtime reconciliation contract. It shows match status, historical coverage, source coverage and explicit warnings without duplicating business logic in React.

### Opportunities

The React Opportunities view consumes the structured `dashboard_snapshot.opportunity_set` contract returned by the Orchestrator. It presents eligible opportunities, action candidates, rejected opportunities, quality and provenance metadata without recalculating ranking, valuation, capital or risk in TypeScript.

The current Dashboard deterministic snapshot does not itself manufacture market opportunities: when no `OpportunitySet` is supplied by the upstream workflow, the UI explicitly shows that no OpportunitySet is available. This keeps the UI honest and avoids inventing investment opportunities from incomplete market inputs.

### Copilot

Provides the Golden Conversational Cases C01–C08 and sends questions to `POST /orchestrate`. The response surface exposes synthesis, decision proposal, risk validation, opportunity count, data quality, provenance and evidence.

## Communication pattern

For analytical views:

```
React Dashboard
    |
    | POST /orchestrate
    v
FastAPI Orchestrator Server
    |
    v
B3 Orchestrator / LangGraph
    |
    v
Deterministic engines + governed reasoning
    |
    v
Structured response
    |
    v
React Dashboard
```

Uploads are separate ingestion endpoints. Portfolio/options Excel files replace the active snapshots. Brokerage-note PDFs are parsed into the persistent option ledger and source manifest; the runtime subsequently reconciles that ledger with the active options snapshot.

## Data quality principle

The Dashboard must distinguish:
- VALIDATED: data passed the relevant loader/validation path.
- WARNING: data is usable with explicit caveats.
- REJECTED: data must not drive an investment action.
- STAGED: a source file has been stored but has not yet been incorporated into the analytical ledger.

## Current limitations

- Brokerage-note PDFs are parsed into the option ledger. Runtime reconciliation exposes `RECONCILED`, `POTENTIAL_DUPLICATE`, `EXCEL_ONLY` and `BROKERAGE_ONLY` relationships without feeding both sources into P&L.
- Opportunities UI is implemented against the OpportunitySet contract; upstream production of a populated OpportunitySet for the Dashboard remains a separate integration step.
- Dashboard validation is still in progress.

## Source of truth

Software behavior and versioned technical documentation are maintained in GitHub. Dashboard behavior should be documented from the implemented code and tests, not from an aspirational architecture.
