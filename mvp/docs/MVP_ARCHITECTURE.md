# MVP Architecture

## Principle

The Dashboard and MCP are two interfaces over the same deterministic B3 Agent domain layer. They must not duplicate portfolio calculations or opportunity ranking.

## Runtime model

```text
BTG XLSX
   |
   v
BtgRendaVariavelLoader
   |
   v
PortfolioContext
   |
   +--------------------+
   |                    |
   v                    v
Portfolio           Opportunity
Intelligence        Intelligence
   |                    |
   +----------+---------+
              |
              v
       Interface Layer
        /           \
       /             \
Dashboard            MCP
  |                    |
Human                  AI Agent
```

## Dashboard

The first dashboard should provide four views:

### Overview

- portfolio as-of date
- position count
- portfolio exposure
- capital/risk indicators
- stock versus option composition
- data quality

### Portfolio

- all normalized positions
- ticker, instrument type, quantity, value and weight
- option metadata when applicable
- filtering and position selection

### Options

- calls and puts
- underlying exposure
- expiration
- assignment/delivery exposure
- covered-call context

### Opportunities

- ranked opportunities
- action type
- valuation attractiveness
- expected return
- risk
- capital requirement
- portfolio fit
- rationale/evidence references

## Interaction model

Selecting a position should expose its current portfolio context and the relevant alternative opportunities. The dashboard is decision-support only.

## MCP

The MCP server exposes read-only domain capabilities. It is an AI-facing interface, not the decision engine and not an order gateway.

Current live tools on `feature/mcp-mvp`:

- `get_system_capabilities`
- `get_portfolio_context`
- `get_portfolio_intelligence`

The broader Phase 7 tool surface will be implemented only when the underlying deterministic capabilities are real and tested.

## Data governance

The user's BTG workbook remains outside Git. The dashboard must consume a configured local source and must fail explicitly when the source is unavailable. No financial mock data should be added to production code.
