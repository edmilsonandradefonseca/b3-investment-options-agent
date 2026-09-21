# B3 MCP MVP

## Purpose

Expose the B3 Investment Intelligence domain to MCP-compatible AI clients through a governed tool boundary. Domain analysis remains read-only; Obsidian memory uses controlled writes.

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
    +-- Obsidian Memory (controlled write)
```

## Governance principles

- Domain intelligence tools are read-only; memory tools are controlled-write operations.
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
- `search_memory`
- `read_memory`
- `write_memory`

The first implementation establishes the MCP boundary and governance contract. Domain-specific tools are added incrementally behind this boundary without changing the deterministic core.
