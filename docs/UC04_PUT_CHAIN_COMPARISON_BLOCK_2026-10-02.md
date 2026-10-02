# UC-04 PUT multi-strike comparison — 02/10

## Scope

Adds an additive live-chain comparison to Strategy Lab. It keeps the frozen
V4.3 routes and existing OPLAB adapter, compares only explicitly selected
contracts, and does not add a table, ledger, provider acquisition path, or React
financial calculation.

## Deterministic contract

- Accept 2–20 unique exact option identifiers for one explicit ticker.
- Load the existing current option snapshot once. Each identifier must resolve
  to one PUT contract and one quote in that response. All candidates must have
  the same exact future expiry and a positive current bid. Missing candidates,
  duplicates, wrong types and unavailable bids fail closed.
- Report quote as-of/source, spot, strike, expiry, multiplier, bid/ask/mid,
  available IV/Greeks, spread, volume/OI, one-contract premium, collateral,
  break-even and maximum loss before fees/taxes.
- Scenario payoff at expiry is `(bid − max(strike − terminal spot, 0)) ×
  contract multiplier`; comparison shocks are explicit user inputs. Optional
  `MAXIMIZE_WORST_CASE_RETURN_ON_CAPITAL` uses strike collateral and is
  conditional only on the supplied shocks. It has no probability weighting.
- P(ITM) at expiry and P(touch) are separate, uncalibrated lognormal proxy
  estimates. Inputs are current spot and an unambiguous annualized decimal IV;
  assumptions set rate and carry to zero and are included in output. Missing or
  ambiguous IV leaves both values UNKNOWN. These are not calibrated real-world
  odds, nor assignment probabilities.
- `maturity_type` is surfaced as a provider-reported field only. Missing or
  unrecognized style is UNKNOWN. No American early-assignment model is run.
  Personal assignment frequency stays UNKNOWN without eligible personal
  outcomes and PIT entry evidence in this request.

## Integration

`FastRouteDispatcher` recognizes `put_candidate_option_ids` on the existing
Strategy Engine route. The frontend lists PUTs from Ativo A's current chain and
requires a shared expiry. The user selects the exact contracts and can reuse the
existing horizon, shock and objective controls. `AnalysisOutput` presents
contract facts, modeled values, scenario payoffs and limitations separately.

No Opportunities ranking, Market Intelligence price-target ingestion, Copilot
AC-28 orchestration or AC-27 navigation continuity is claimed by this block.
UC-07/08/09 evidence does not affect a rank because eligible personal outcome
samples remain unavailable.

## Local verification and real acceptance

- Python compilation and `git diff --check`: PASS.
- TypeScript/Vite production build: PASS.
- Local focused pytest could not run in the reset sandbox: Python 3.12 runtime
  has no pytest or project dependencies. GitHub CI #1287 passed all 796 Python
  tests and the React build on final code commit `b2fb05e`.
- The earlier CI runs exposed two concrete regressions: missing Strategy Lab
  route recognition for explicit candidate IDs and a fixture timestamp later
  than its requested as-of. Commits `7b43ac4` and `b2fb05e` corrected these;
  final CI is green.
- Live-provider/UI acceptance is still pending. OPLAB availability remains an
  external gate; no mock chain is described as real acceptance.

Ubuntu acceptance after CI passes: update the checkout with
`git pull --ff-only origin feature/react-functional-v43-integration`, restart
`b3-runtime.service`, open Strategy Lab, set Ativo A to a ticker and strategy A
to “Vender PUT”, select one expiry and at least two current contracts, then
compare with explicit shocks. Check the quote as-of, exact IDs, separate P(ITM)/
P(touch), UNKNOWN personal frequency, provider-reported exercise style and
limitations. If live quote coverage is incomplete, record INCOMPLETE and its
source error; do not substitute fixtures or adjacent strikes.
