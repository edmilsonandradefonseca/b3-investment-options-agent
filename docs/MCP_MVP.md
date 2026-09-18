# B3 MCP MVP

## Purpose

Expose the B3 Investment Intelligence domain to MCP-compatible AI clients through a governed, read-only tool boundary.

## Architecture

```text
MCP Client
    |
    v
B3 MCP Server
    |
    v
Deterministic B3 Domain Engines
    +-- Portfolio Intelligence
    +-- Options Analysis
    +-- Valuation
    +-- Opportunity Intelligence
    +-- Market Context
```

## Governance principles

- MCP tools are read-only.
- MCP does not place or construct executable orders.
- Deterministic calculations remain authoritative.
- LLM reasoning consumes structured domain outputs; it does not replace upstream calculations.
- Tool contracts should preserve provenance, quality status and as-of timestamps where supplied by the domain layer.
- Opportunity outputs are decision-support candidates, not investment instructions.

## Initial tool surface

- `get_system_capabilities`
- `get_portfolio_context`
- `get_portfolio_intelligence`
- `analyze_position`
- `get_valuation`
- `get_opportunities`
- `compare_position_opportunity`
- `get_market_context`

The first implementation establishes the MCP boundary and governance contract. Domain-specific tools are added incrementally behind this boundary without changing the deterministic core.
