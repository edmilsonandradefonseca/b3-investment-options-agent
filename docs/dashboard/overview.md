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

### Opportunities

Navigation entry exists, but the current React page is still a placeholder. The next implementation must consume the existing OpportunitySet/Opportunity Intelligence backend rather than reimplementing business rules in TypeScript.

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

Uploads are separate ingestion endpoints. They update/stage the runtime data source and are subsequently consumed by the Orchestrator.

## Data quality principle

The Dashboard must distinguish:
- VALIDATED: data passed the relevant loader/validation path.
- WARNING: data is usable with explicit caveats.
- REJECTED: data must not drive an investment action.
- STAGED: a source file has been stored but has not yet been incorporated into the analytical ledger.

## Current limitations

- Brokerage-note PDFs are currently staged; parsing into the option ledger is a separate contract.
- Opportunities UI is not yet implemented.
- Dashboard validation is still in progress.

## Source of truth

Software behavior and versioned technical documentation are maintained in GitHub. Dashboard behavior should be documented from the implemented code and tests, not from an aspirational architecture.
