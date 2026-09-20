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

The React E2E validates the UI/boundary contract with a mocked structured Orchestrator response. In addition, `tests/test_copilot_golden_workflow.py` executes all eight scenarios through the **real LangGraph workflow**, including deterministic context propagation, capital governance, synthesis, decision schema and the real `RiskValidator`. The workflow test uses deterministic specialist/knowledge/reasoning doubles so CI does not depend on external LLM credentials. Therefore this is real workflow integration coverage, but not an external-LLM production acceptance test.

See:
- `docs/dashboard/use-cases.md`
- `docs/dashboard/testing.md`

These cases are validation scenarios, not autonomous trading instructions.
