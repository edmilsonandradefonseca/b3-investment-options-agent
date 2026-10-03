# BUY pair evidence projection — 2026-10-03

Code: `72c2032f827e6b5c1b561e011c88235f637124f5` (implementation `f701809`, canonical capital validator correction `f648b35`). PR #66 remains draft.

Existing BUY_STOCK × BUY_STOCK StrategyComparison now adds stock_purchase_comparison without creating a second economic engine or data store. API and central frontend table expose per-alternative quote/capital, source-qualified observed fundamentals, historical risk, portfolio evidence and forward-forecast gaps. The senior receives the same additive deterministic payload through existing workspace context. No provider is added and no numeric forecast or price target is invented.

Fundamental metric deltas require equal report date, period type and explicit units. Unsupported/future/nonfinite/rejected/unattributed metrics are excluded in this new projection with reason. Quote availability/observation/finiteness and seven-day age are checked. Current BUY cutoff freezes after acquisition; explicit historical cutoffs are not advanced. These checks qualify the new projection, not a claim that all preexisting asset_evidence paths now have strict PIT admissibility.

Future dividends, positive-return probability, expected return and institutional targets remain UNKNOWN without qualified forecast evidence. Historical volatility/drawdown cannot become a future-return preference. This delivers transparent evidence presentation and comparison eligibility, not the complete economic BUY recommendation requested by the user.

Validation: GitHub CI #1370 SUCCESS, 851 Python tests PASS in 9.73 seconds, React build PASS, human-facing rendering regression PASS. Four focused projection checks cover comparability, future availability/report, stale quote and preserved forecast UNKNOWN. Local pytest dependencies unavailable; focused assertions executed directly and full tests ran independently in GitHub.

Real gate: https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37144640150 was pending at checkpoint. Earlier candidate run 37144529580 was queued. No actual Ubuntu BUY acceptance, synthesis latency, service activation or Windows visual E2E is claimed. Validator uses canonical comparison_amount=10000, ITUB4/BBDC4, zero-LLM deterministic acceptance followed by one structured senior comparison. Private payloads stay on Ubuntu; Actions outputs metadata only.

Do not ask for runtime restart before the real candidate gate passes. Next: inspect final Ubuntu workflow, fix any concrete failure, record available fundamentals/forecast gaps, then activate once and verify active API. Dividend forecasts/announced-event entitlement and institution-sourced targets remain separate implementation/data work; do not label this block a fulfilled future-return forecast or superiority to ChatGPT.

## Actual Ubuntu candidate acceptance — 2026-10-03 16:42 BRT

Final workflow 37144640150 SUCCESS at code 72c2032. ITUB4/BBDC4 deterministic HTTP 200 in 1737.1 ms, zero LLM calls, two alternatives, 15 and 3 admitted fundamental metrics respectively. Senior HTTP 200 with two canonical alternative assessments in 55485.1 ms. Future forecast remains UNKNOWN. This validates output structure and actual source availability, not independently graded economic reasoning or forecast accuracy. First superseded candidate f701809 admitted zero metrics; final cutoff fix restores 15/3 without advancing historical cutoffs.

Ubuntu checkout updated to 72c2032. RUNTIME_RESTART=BLOCKED: sudo requires authentication. Active HTTP baseline checks passed but do not establish new BUY block activation. Next required operator action: sudo systemctl restart b3-runtime.service, followed by focused active HTTP verification. Windows frontend update/render acceptance remains pending. No stable latency gain is inferred from this single senior measurement.
