# Dashboard Golden Use Cases

The Dashboard Copilot currently exposes eight Golden Cases:

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

Golden Case text and automated assertions live with the Dashboard tests and frontend implementation. These cases are validation scenarios, not autonomous trading instructions.
