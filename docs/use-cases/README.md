# Dashboard Golden Use Cases

The Dashboard Copilot exposes eight Golden Cases:

| ID | Name | Primary validation |
|---|---|---|
| C01 | Opportunity Discovery | OpportunitySet + available capital |
| C02 | Capital Insufficient | Capital requirement rejection |
| C03 | Diversification | Portfolio context + opportunities |
| C04 | Position vs Opportunity | Existing position vs relative opportunity |
| C05 | BUY vs SELL PUT | Strategy comparison with evidence |
| C06 | Valuation | Deterministic valuation context |
| C07 | Existing PUT | Existing option position + alternatives |
| C08 | Insufficient Evidence | Evidence/governance behavior |

## Current test status

All eight cases are present in the React Copilot and are asserted by the Dashboard E2E.

The E2E currently validates the UI/boundary contract and uses a mocked structured Orchestrator response. Therefore C01–C08 are **not yet equivalent to real end-to-end workflow validation**.

See:
- `docs/dashboard/use-cases.md`
- `docs/dashboard/testing.md`

These cases are validation scenarios, not autonomous trading instructions.
