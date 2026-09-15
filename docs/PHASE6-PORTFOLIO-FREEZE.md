# Phase 6 — Portfolio Intelligence Freeze

Status: **FROZEN**

## Scope completed

Phase 6 establishes deterministic portfolio intelligence for existing positions:

- normalized `Position` and `PortfolioContext`;
- portfolio exposure grouped by underlying;
- signed market values for long/short positions;
- short PUT assignment-capital calculation;
- short CALL deliverable-share and coverage calculation;
- deterministic realized/unrealized P&L separation;
- premium received and buyback cost kept separate;
- explicit position lifecycle state machine;
- deterministic capital-risk snapshot;
- per-position assessment;
- composed portfolio intelligence context;
- golden portfolio cases covering stock, short PUT, covered CALL, mixed stock/options, lifecycle roll/replace, insufficient cash and uncovered calls.

## Invariants

1. Position quantities and signed market values preserve broker semantics.
2. Contract multipliers are configuration/data fields, never hardcoded in portfolio positions.
3. PUT assignment capital is `abs(quantity) × strike × contract_multiplier`.
4. Covered-call coverage is based on deliverable shares, not contract count alone.
5. Realized and unrealized P&L remain separate.
6. Premium received is not inferred from market value.
7. Lifecycle transitions are explicit and deterministic.
8. Capital risk never places or executes orders.
9. No LLM participates in Portfolio Intelligence calculations.
10. Phase 6 produces context; investment action ranking remains Phase 7+.

## Validation

GitHub Actions CI is green on the final Phase 6 implementation commit. The test suite completed successfully after fixing a floating-point equality assertion and correcting the golden-test engine import collision.

## Known boundary

P&L calculation is implemented as a deterministic engine, but transaction-history-derived realized P&L is not synthesized by the portfolio context because the current `Position` contract does not contain transaction history. This remains an explicit input boundary for future persistence/portfolio-history work and is not silently inferred.

## Next phase

Phase 7 — Opportunity Ranker.

The ranker will compare existing-position intelligence with newly generated BUY / ACCUMULATE / SELL PUT / SELL CALL / HOLD-WAIT / REDUCE / SELL / AVOID opportunities. It must remain deterministic for scoring and eligibility; LLM reasoning is deferred to the later LLM Gate and Investment Committee phases.
