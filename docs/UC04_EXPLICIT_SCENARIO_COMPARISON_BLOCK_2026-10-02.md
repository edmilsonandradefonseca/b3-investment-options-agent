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

GitHub CI #1282 for commit `f8f975f` passed (Python regression and frontend
production build); the 791-test Python suite, TypeScript/Vite build and diff
check also pass locally. Ubuntu and Windows UI acceptance remain pending. It
must inspect a real selected contract whose expiry matches the horizon, and
confirm each explicit shock's P&L displays with no winner/probability. This
increment does not complete the objective/constraint policy, PUT-chain ranking,
funded sell-to-buy accounting with transaction costs/taxes, or Opportunities
ranking. Those remain subsequent blocks; AC-01…AC-26 are not accepted by these
fixtures.

## B2 — explicit scenario objective and normalized ranking

The follow-up adds an opt-in objective `MAXIMIZE_WORST_CASE_RETURN_ON_CAPITAL`;
the default remains `COMPARE_ONLY`. It ranks only when both alternatives have
P&L for every user-entered shock and a known, positive denominator:

- BUY_STOCK: the explicitly supplied comparison amount;
- SELL_PUT: strike × contract multiplier (cash-secured collateral);
- covered SELL_CALL: one covered contract's underlying notional;
- HOLD/SELL_STOCK: the known current underlying position's market value.

For each alternative the policy computes each provided scenario return as
`scenario P&L / stated capital basis`, then selects the larger minimum return
over only that user-defined scenario set. Missing P&L/base produces
`UNAVAILABLE`; equal minima produce `TIE`; otherwise the response reports
`CONDITIONAL_RANKING` with both alternatives' worst-case returns. This is a
deterministic maximin rule over a chosen finite set, not a forecast, expected
return, probability, full portfolio utility or universal recommendation. The
base, source label, each scenario return and limitations are rendered. Costs,
taxes, slippage, financing, capital constraints outside these denominators and
objective trade-offs remain outside B2.

Review-driven requirements were also added to the delivery matrix: AC-27
cross-workspace continuity, AC-28 multi-alternative Copilot orchestration, and
an AC-16 gate that leaves early-assignment risk `UNKNOWN` if contract exercise
style/terms are unavailable. Those product flows and the option-chain / model
probability work remain unimplemented here.

For B2 verification, regression now covers default no-ranking behavior, a
conditional maximin result for a stock-versus-PUT comparison with a common known
R$5,000 capital basis, and dispatch of the explicit objective from Strategy Lab.
The current managed scratch session no longer contains the Python 3.14 test
environment and outbound package downloads are blocked; Python source compilation
and TypeScript/Vite build pass locally. B2 was published as `942326f` and CI
#1284 passed (Python regression and React build). The follow-on multi-strike PUT
block and its final CI are documented in
`docs/UC04_PUT_CHAIN_COMPARISON_BLOCK_2026-10-02.md`.
