# Phase 4 — Valuation Freeze

**Status:** FROZEN
**Date:** 2026-09-14

## Scope

Phase 4 implements deterministic stock valuation and the investment price-policy layer.

### Valuation methods

- P/E for non-financial companies.
- EV/EBITDA for non-financial companies.
- DCF/FCF for non-financial companies.
- P/B + ROE for financial companies, using justified P/B:
  `P/B = (ROE - g) / (Ke - g)`.

All methods produce Bear/Base/Bull valuation ranges through `ValuationRange` and preserve assumptions/source references for auditability.

### Investment Price Policy

The policy is a separate deterministic layer after fair-value estimation:

- Accumulation Price = Base Fair Value × (1 − explicit margin of safety).
- Reduce Price = Base Fair Value.
- Sell Price = Bull Fair Value.
- Current Margin of Safety is calculated when current market price is supplied.

The policy does not modify the underlying valuation and does not autonomously emit BUY/SELL decisions.

## Validation

Phase 4 includes unit coverage for each valuation method and integration coverage from valuation through Investment Price Policy. Invalid inputs and scenario-order violations are rejected deterministically.

CI must remain green before subsequent phases are started.

## Architectural impact review

- Component responsibility: unchanged.
- LangGraph flow/state: unchanged.
- Public valuation contract: unchanged for this freeze.
- New data source: none.
- New LLM call: none.
- Look-ahead/data leakage risk: no new risk introduced; PIT remains upstream requirement.
- Investment-decision regression risk: covered by deterministic tests; policy remains separate from decision engine.

## Phase boundary

This freeze does **not** implement Options, Portfolio, RAG, LLM Gate, Investment Committee, Risk, or execution. Those remain subsequent roadmap phases.
