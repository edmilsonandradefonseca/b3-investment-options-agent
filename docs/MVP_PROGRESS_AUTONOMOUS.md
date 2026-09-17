# MVP Autonomous Development Progress

## Scope

Autonomous development is limited to `feature/mcp-mvp`. `main` must remain untouched.

## Current architecture

BTG portfolio state → PortfolioContext

BRAPI → stock market information
OpLab → options market information

Deterministic engines → quant / valuation / opportunity analysis

OpportunitySet → deterministic reasoning context → LangGraph → Obsidian/RAG → risk validation → decision proposal

The LLM does not fetch data, calculate valuation, rank opportunities, or override deterministic risk barriers.

## Current workstream

1. Integrate stock market observations with the deterministic stock opportunity producer.
2. Add real OpportunitySet assembly from stock and options producers.
3. Preserve point-in-time availability and source provenance.
4. Add golden/regression tests for deterministic behavior.
5. Integrate the resulting OpportunitySet into the reasoning context.
6. Only after backend validation, replace the dashboard placeholder with real opportunities.
7. Extend MCP surface only where the underlying backend contract is already real.

## Explicit non-goals

- No execution/trading automation.
- No LLM-based ranking.
- No invented valuation from market prices.
- No direct external-data-to-decision path.
- No changes to `main`.

## Validation requirement

Every new deterministic integration must have focused tests and must preserve existing contracts. If CI execution is unavailable through the GitHub connection, mark validation as pending rather than claiming it passed.
