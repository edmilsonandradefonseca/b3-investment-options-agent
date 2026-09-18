# MCP Portfolio Context — MVP

## Purpose

The first real MCP vertical slice exposes the deterministic `PortfolioContext` through `get_portfolio_context()`.

The MCP server does not fabricate portfolio data. It reads a configured JSON snapshot and returns the normalized domain object.

## Source configuration

By default the server reads:

```text
data/portfolio.json
```

Override the source with:

```text
B3_AGENT_PORTFOLIO_FILE=<absolute-or-relative-path-to-json>
```

## JSON contract

```json
{
  "as_of": "2026-09-15",
  "cash": 10000,
  "source_refs": ["manual:portfolio"],
  "quality_status": "VALIDATED",
  "positions": [
    {
      "position_id": "POS-001",
      "ticker": "ITUB4",
      "instrument_type": "STOCK",
      "quantity": 100,
      "average_cost": 30.0,
      "market_price": 35.0,
      "market_value": 3500.0,
      "source_ref": "manual:portfolio"
    }
  ]
}
```

For option positions, `strike`, `expiration_date` and `option_type` are required by the existing `Position` schema.

## MCP tools implemented

### `get_portfolio_context()`

Returns the point-in-time normalized portfolio snapshot.

### `get_portfolio_intelligence()`

Feeds the same real `PortfolioContext` into `PortfolioIntelligenceEngine` and returns deterministic assessments, exposures and capital-risk context.

## Governance

- Read-only.
- No broker order execution.
- No LLM calculation of portfolio metrics.
- Missing source is an explicit error.
- Source provenance and `quality_status` are preserved.
- The JSON file is an MVP adapter; it can later be replaced by the structured SQLite/Parquet repository without changing the MCP tool contract.
