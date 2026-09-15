# Dashboard MVP

The dashboard is the human-facing interface of the B3 AI Investment Copilot.

## First implementation target

Build a local web dashboard over the existing `b3_agent` services. The dashboard must reuse the deterministic portfolio ingestion and intelligence engines rather than reproduce calculations in UI code.

### Views

1. **Overview** — portfolio snapshot, exposure and quality.
2. **Portfolio** — searchable/filterable normalized positions.
3. **Options** — calls, puts, expirations and exposure.
4. **Opportunities** — Phase 7 ranked opportunities.
5. **Position analysis** — current position versus candidate alternatives.

## Non-goals

The dashboard does not execute orders, call a broker for trading, or allow an LLM to override deterministic facts.

## Data source

For the local MVP, configure `B3_AGENT_PORTFOLIO_FILE` to the user's BTG `.xlsx` workbook. Do not copy the private workbook into the repository.
