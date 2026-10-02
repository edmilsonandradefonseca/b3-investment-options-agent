# UC-04 explicit terminal-price scenario comparison — 2026-10-02

## Purpose and boundary

This is the first bounded economic-comparison increment after source-first
research. It reuses the current `LiveStrategyComparisonService`,
`StrategyComparisonEngine`, `AssetEvidencePack`, portfolio snapshot and explicit
OPLAB contracts. It adds no store, schema, V4.3 route family, or ranking ledger.

The Strategy Lab accepts a common future horizon and up to nine explicit
underlying price shocks (percent values, bounded to -90%…+300%). The user owns
these assumptions. The backend computes deterministic terminal P&L for the
existing two alternatives:

- BUY_STOCK: hypothetical shares purchased with the explicit comparison amount;
- HOLD: known shares in the supplied portfolio snapshot;
- SELL_STOCK: known remaining shares after the existing notional what-if;
- SELL_PUT: current bid premium less terminal intrinsic loss for one cash-secured
  contract;
- covered SELL_CALL: current bid, covered-share price change and terminal call
  intrinsic value for one contract.

Option payoffs are computed only when the supplied common horizon exactly equals
the identified current contract's expiration date. If the option horizon or
required capital/position facts do not match, that alternative's payoff remains
empty and the comparison is `PARTIAL` or `UNAVAILABLE`. The existing source refs,
quote/asset `as_of`, coverage checks, and quality status remain in the response.

## Authority

- A scenario is a deterministic what-if, not a forecast, distribution, expected
  return, market probability, assignment probability, or historical outcome.
- No shock is generated from volatility or personal history. Probabilities remain
  `null`; ranking remains `NOT_APPLIED`.
- Unknown share quantity, amount, quote or unsupported common horizon is not zero.
- The option uses the explicit OPLAB contract, its multiplier and current bid;
  no sibling contract is substituted. Early assignment, financing, taxes, fees,
  slippage and execution-lot rounding remain outside this payoff.
- Historical UC-07/08/09 evidence remains a separate context. No observed
  execution is promoted into an outcome or a ranking weight.

## Verification

Focused regression covers BUY_STOCK versus cash-secured PUT, covered CALL payoff,
common-expiry enforcement, mismatch reporting, bounded/unique shock validation,
dispatch wiring and pairwise scenario deltas. `tests/test_strategy_live.py` and
`tests/test_fast_dispatch.py` pass. All 791 Python tests pass when the existing
local reasoning lock is configured under writable `/tmp` (the managed sandbox
mounts `/var/lock` read-only). TypeScript/Vite production build passes.

The Ubuntu and Windows UI acceptance is pending publication and green CI. It
must inspect a real selected contract whose expiry matches the horizon, and
confirm each explicit shock's P&L displays with no winner/probability. This
increment does not complete the objective/constraint policy, PUT-chain ranking,
funded sell-to-buy accounting with transaction costs/taxes, or Opportunities
ranking. Those remain subsequent blocks; AC-01…AC-26 are not accepted by these
fixtures.
