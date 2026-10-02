# Decision-specific history — 2026-10-02

## Pre-code authority and matrix

Restart/handoff and their authority set remain binding, especially UC-07/08/09,
the frozen V4.3 boundaries and the prior observed-lifecycle admission block.
GitHub HEAD `a9b1d3e`, PR #66 open/draft, CI #1275 SUCCESS were verified.
The user reports the Portfolio received-income block working and authorizes
continuation into Opportunities, Strategy Lab and Copilot. This is scoped user
acceptance, not independent verification of production historical coverage.

| Area | State before this block | Additive next step |
| --- | --- | --- |
| SQLite history / observed lifecycle | Fully implemented; scoped Ubuntu PASS | Reuse existing read projection |
| Historical admission / PIT filters | Fully implemented for available observations | Preserve strict availability and UNKNOWN |
| Alternative/contract-specific precedent | Missing implementation | Exact-symbol projection bound to deterministic candidate IDs |
| Canonical Experience/Learning algorithms | Implemented but production structured loaders not wired | Do not invent eligible experiences or store another ledger |
| Final outcomes, entry IV/regime, full account coverage | Missing real data | Expose requirements, no winner/success rate |
| Candidate history comparison in shared analysis view | Frontend-only gap | Shared additive evidence panel |

## Selected scope

Bind history to the existing StrategyComparison alternatives and OpportunitySet
candidates, plus an explicit Copilot ticker fallback. Exact contract matching
must not pull sibling contracts sharing a four-letter root. Existing asset-level
history keeps its clearly marked unverified root observations for compatibility.
Observations are source-linked and bounded; repeated subjects reuse one exact
projection. No market acquisition, new table, finalized outcome, learning
activation or historical ranking change is introduced. Current chain metadata
must never become historical entry features.

## Remaining gates

Complete UC-07/08/09 requires canonical account/contract coverage, terminal
settlement/linked roll evidence, PIT entry/management/exit snapshots, final
outcomes and canonical persisted learning versions. OPLAB remains the previously
documented external gate; do not repeat network diagnostics. Production batch
import receipt remains separate from the supplied-source audit.

## Implemented behavior and validation

- `decision_history` references candidate/alternative IDs without rewriting their
  deterministic ordering or economics. Its subject dictionary holds each exact
  projection once, even when two actions use the same symbol.
- Strategy Lab uses `subject_id`; Opportunities uses the selected contract's
  `options_analysis_ref` (stock candidates use their ticker). A missing option
  identity cannot be substituted with a stock history. Copilot can use the
  explicit ticker, or candidate context already available in the workflow.
- Exact matching shares the existing bounded raw SQLite cache and revision/WAL
  invalidation. Its fingerprint includes match policy. Date, availability and
  since-window reconstruction rules are preserved; no entry market features are
  backfilled from the present.
- Shared analysis displays per-candidate execution/sequence/eligible counts and
  unavailable similarity. Sources, movements, cutoff, omissions and gates are
  expandable once per subject. Generic asset/root observations remain separately
  expandable and explicitly unverified.
- The execution projection admits no canonical outcomes/learnings. It is not a
  replacement for typed ExperienceContextService or POST-OUTCOME learning.
  Missing contrary evidence is not confirmation of a thesis.
- Read-only `/history/decision-context?ticker=EXACT_SYMBOL` exposes the same
  deterministic projection without models/providers. Blank tickers and naive
  historical cutoffs are rejected.

Verification: 734 Python regression tests PASS; TypeScript/Vite build PASS.
Tests cover sibling-contract exclusion, preserved candidate order/limits,
shared-subject reuse, zero/unknown semantics, future/missing import availability,
revision invalidation, since-window legs, agent/API/workspace wiring and no
database write. No OPLAB diagnosis or market collection was repeated.

After publication and green CI, the focused Ubuntu gate is:

```bash
cd /opt/b3-investment-options-agent && \
git pull --ff-only origin feature/react-functional-v43-integration && \
sudo systemctl restart b3-runtime.service && \
./.venv/bin/python scripts/validate_decision_history_real.py
```

The validator selects an already observed symbol (or PETR4 if empty), checks
exact matching and strict cutoff without changing data, and explicitly does not
claim complete UC-07/08/09 validation. Desktop acceptance should check the new
shared evidence section in Opportunities, Strategy Lab and Copilot. Existing
observed-lifecycle and income import gates do not need repeating.

## Real Ubuntu acceptance — 2026-10-02 10:51 America/Sao_Paulo

The user supplied the actual terminal output after fast-forwarding from
`a9b1d3e` to `53c5682`, restarting `b3-runtime.service` and running
`scripts/validate_decision_history_real.py`.

Result: **PASS EXACT DECISION HISTORY + STRICT CUTOFF**.

| Observation | Retrospective | Strict known-at-time |
| --- | --- | --- |
| Exact symbol | XPBRJ100 | XPBRJ100 |
| Matching executions | 2 | 2 |
| Observed sequences | 1 | 1 |
| Eligible outcomes | 0 | 0 |
| Exclusions | None reported | None reported |

Both reads reported `option_transactions` READ_OK / 264 rows,
`transactions` READ_OK / 0 rows and `source_manifest` READ_OK / 119 rows,
all untruncated. The earlier single-execution/missing-manifest runtime snapshot
is therefore superseded for the current loaded source counts. The 264 count
agrees with the supplied batch audit count; this output alone does not establish
row-by-row reconciliation, complete account coverage or 119 unique notes.

Strict mode uses the validation-time cutoff, not an independently tested past
decision date. Its two admitted executions have proven availability by that
cutoff. This is not acceptance of full historical replay, final outcomes,
assignment/expiry/roll reconstruction, learning or calibrated similarity.
Opening balances, economic outcomes and eligible comparable samples retain the
documented UNKNOWN/gates. Desktop evidence rendering remains a separate gate.

The focused Ubuntu gate is complete. Do not request this command again without
a new implementation or specific regression hypothesis. Next work must use the
current loaded stores and identify canonical terminal/PIT evidence and the
existing Experience/Learning production wiring before admitting any outcome;
no replacement ledger or repeated source/network discovery is authorized by
this acceptance.
