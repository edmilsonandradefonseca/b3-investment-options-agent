# UC-07/08/09 production failure and implementation gap analysis — 2026-10-02

## Production incidents reported after `bb650ee`

### Shared Opportunities, Market Intelligence and Copilot failure

The user reported `Message file not found: -` from Opportunities, Market
Intelligence and the B3 Agent. These paths converge on
`OpenClawStructuredClient.complete_json`. The deployed code passed
`--message-file -` and also wrote the prompt to subprocess stdin. The Ubuntu
OpenClaw CLI treated `-` as a literal filename and rejected it. This is a
client/CLI transport incompatibility introduced by the previous fix, not three
independent workspace failures and not evidence that the market-data sources
failed. The previous CI test asserted the unsupported dash convention, so its
green result did not cover the installed CLI behavior.

Correction: write the complete prompt to a uniquely named mode-0600 temporary
file, pass that path to `--message-file`, and remove it on success, timeout or
launch error. No prompt is placed in argv or truncated. A regression test reads
the file from the fake process, asserts that a 256 KB prompt is intact, and
verifies cleanup and file permissions.

### Strategy Lab ticker failure

The reported provider error names `WWEGE3`. Source inspection shows the React
form applies only `toUpperCase()` and the backend applies only uppercase/strip;
neither prepends `W`. The request/provider boundary therefore received or
produced `WWEGE3`; available evidence cannot determine whether that value was
typed, retained in the UI, or changed outside this code path. The old boundary
sent it to both history providers, producing a low-level OPLAB no-data and
BRAPI HTTP 400 instead of a useful input error.

Correction: validate the B3 equity ticker shape (`four letters + one or two
digits`) before any market/fundamentals provider call in the Strategy Lab
service. Keep the exact invalid input in the error and do not autocorrect it.
`WEGE3` passes shape validation; only live provider evidence can establish that
its requested history is available.

## What is implemented and what remains incomplete

| Surface / UC | Working implementation | Why the advanced case still is not ready |
| --- | --- | --- |
| Opportunities / UC-07, 08, 09 | Candidate generation and current option marketability; exact-symbol observed-execution projection; bounded history/research context can be attached to candidates. | Live opportunity path sorts candidates by expiry/strike/ID and reports `DEFERRED_INCOMPLETE_CONTEXT`. It is per-underlying, not a cross-universe economic ranker for holdings plus watchlist/outside names. Past observations do not affect order. |
| Strategy Lab / UC-07, 08, 09 | Exact-subject decision history reaches comparisons; UC-04 B1/B2/B3A provide user-specified price-shock payoffs, explicit maximin over those shocks, and same-underlying/same-expiry PUT-chain comparison. Invalid tickers are now rejected before providers. | UC-07 data is observational rather than a complete account/position lifecycle. UC-08 has no configured canonical production Outcome/Experience/Learning owner. UC-09 has no eligible personal comparable outcomes. Cross-asset funded sell-to-buy, complete objective/constraint ranking, costs and portfolio-wide exposure are not implemented. |
| Market Intelligence / UC-09 | Research reads existing Qdrant/Neo4j B3 evidence before complementary search, with exact ticker, validity/availability, source and duplicate handling; persisted research is not treated as learning. | Current synthesis invokes OpenClaw and was blocked by the shared message-file error. Stored news/events are not a validated precedent corpus and do not establish a winner or a calibrated probability. |
| Copilot / UC-07, 08, 09 | Explicit tickers can be resolved into bounded workspace/history/research context; typed canonical availability is surfaced without trusting user-supplied learning fields. | Senior answer generation uses the same broken OpenClaw transport. Cross-workspace intent orchestration is partial; missing eligible samples correctly prevent personal success-rate conclusions. |

### Evidence behind the UC boundary

The user's real Ubuntu history gate showed 264 option executions and 119 source
manifest rows, but zero eligible final outcomes for XPBRJ100. The focused exact
history gate passed and must not be repeated. The known SQLite schema gate found
no dedicated Operation/Outcome/FeatureSnapshot/MarketRegime/Learning owner in
the three inspected files. The registered-dataset gate declared only
`market_data` in its inspected scope. Those gates do not prove global absence
of unregistered storage; they do establish that no production canonical
experience adapter is configured in the inspected runtime.

Therefore:

- UC-07 currently means exact-symbol execution observations and their known
  movements, with opening balance/outcome/current position kept unknown where
  unverified. It does not yet mean complete entry/during/exit/P&L lifecycle.
- UC-08's canonical event/atomic-commit/replay boundary and typed PRE-ANALYSIS
  seam are implemented and regression-tested, but there is no production owner
  adapter and no verified terminal outcome plus PIT entry/regime evidence to
  admit.
- UC-09 can retrieve stored market research; it cannot produce an eligible
  personal precedent/learning sample. Personal similarity, support,
  contradiction and success rates remain unavailable or zero-eligible, not
  zero-loss and not market probabilities.

`eligible_outcome_count=0`, `ranking_effect=NONE`, and `UNKNOWN` remain correct.
Current ranking must not be delayed merely because this personal component is
missing, but neither should personal history be allowed to rank candidates.

## Acceptance boundary for the next code block

1. Restore OpenClaw synthesis from the deployed CLI using a private temporary
   message file; run the full Python and React CI suites.
2. Reject malformed Strategy Lab B3 tickers locally with an explicit input
   error, before external history/fundamental calls.
3. Request one focused Ubuntu check only after CI is green: short Copilot
   greeting, Opportunities ITUB4, Market Intelligence context, and Strategy Lab
   ITUB4 × WEGE3. Capture each response status and `as_of`/source metadata.
4. Continue the product block with actual decision behavior: portfolio plus
   outside-universe candidates, explicit objective/constraints and comparable
   capital/horizon, deterministic ranking/exclusions, and progression among
   Opportunities, Market Intelligence and Strategy Lab. UC-07/08/09 evidence
   enriches this flow but never fills missing economic facts.
5. Keep production personal learning unavailable until canonical owner and
   verified account/terminal/PIT evidence are proven; do not create a duplicate
   ledger to pass these cases.
