# Phase 4 — Valuation Freeze

**Status:** FROZEN
**Date:** 2026-09-14

## Scope

Phase 4 covers deterministic stock valuation and the Investment Price Policy layer:

- P/E for non-financial companies.
- EV/EBITDA for non-financial companies.
- DCF/FCF for non-financial companies.
- P/B + ROE for financial companies using justified P/B: `(ROE - g) / (Ke - g)`.
- Accumulation, Reduce and Sell price thresholds from explicit policy parameters.

## Separation of responsibilities

Valuation estimates fair value. Investment Price Policy translates fair value into investor price thresholds. Neither layer autonomously emits a BUY/SELL decision.

## Validation

Integration tests cover the path from each valuation method through Investment Price Policy, including preservation of scenario ordering and audit metadata and rejection of invalid policy inputs.

## Architectural impact review

- Component responsibility: unchanged.
- LangGraph flow/state: unchanged.
- Public contract: no new decision-layer contract introduced.
- New data source: none.
- New LLM call: none.
- PIT/data leakage: no new risk; PIT remains upstream.
- Decision regression: deterministic integration coverage added.

## Boundary

Options is the next roadmap phase. Portfolio, RAG, LLM Gate, Investment Committee, Risk, Backtest and execution remain outside this freeze.
