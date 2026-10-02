# UC-07/08/09 — observed lifecycle and admission block

## Checkpoint and pre-code decision

GitHub HEAD verified: `92ed88f0093db7091dea71526b33a88c4c494350`.
PR #66 is open/draft; CI #1269 SUCCESS. Last user-installed code remains
`8bc7cb9`. Read the restart/handoff and their architecture, use-case,
traceability, frontend, review, history/reuse and ADR-0020 authorities.

No production discovery or OPLAB diagnosis is repeated. The previous Ubuntu
read gate remains authoritative: one execution, no complete-account coverage,
no matching PETR4/VALE3/RENT3 history, absent source manifest. The imported
complete batch claimed by the user remains unreconciled; no source is copied,
reingested or presumed lost.

| Capability | Classification before this block | Additive work / gate |
|---|---|---|
| Read-only execution projection/cache | fully implemented | Reuse the existing read adapter and cache |
| SQLite history in workspaces and Copilot | fully implemented in limited scope | Extend the same payload, not another ledger |
| Partial reductions / outstanding observed deltas | missing implementation in production projection | Reuse OperationReconstructor; distinguish observation from economic lifecycle |
| UC-09 ranker / PRE-ANALYSIS service | implemented but not wired integrally | Prevent future/provisional outcomes and unresolved semantic candidates from becoming precedents |
| Canonical learning validity in PRE-ANALYSIS | implemented but not wired integrally | Filter subject, dates and evidence timestamps before agent exposure |
| Final lifecycle, entry snapshots, personal cohorts | missing real data + missing implementation | Explicit admission gaps; no fabricated experience or learning |
| Persistent POST-OUTCOME with idempotency | missing implementation in runtime composition | Not activated from observed executions |
| Partial lifecycle detail presentation | frontend-only gap | Existing PersonalHistory surface in workspaces/Copilot |
| OPLAB real access / full-path latency | missing real data/access | Independent external gate; no performance claim |

## Canonical entry mapping and smallest block

`option_transactions`: signed quantities, execution price and signed source cost.
`transactions`: explicit BUY/SELL, positive quantity and execution price.
Both already feed the read-only Transaction adapter. Broker/symbol isolation and
same-day ordering exclusions remain. The existing OperationReconstructor can
describe observed increases/reductions and net-flat sequences. Its zero starting
balance is unverified in these stores, so OPEN/CLOSED are not admitted as real
economic outcomes. The read path should not call OutcomeEngine at all.

Repurchase: opposite-side execution reducing the observed delta, not proof of
closing a proven short. Assignment/exercise: require independent settlement and
delivery evidence. Expiry: past expiration or absence of trades is insufficient.
Roll: adjacent buy/sell is insufficient; canonical predecessor/successor,
matched quantities and complete-chain evidence are required. Coverage at entry,
fees, contract identity and PIT entry IV/regime are not supplied by today's
holdings/chain. No multiplier 100 is applied.

The next block is a derived bounded read model: chronological execution movement,
partial reductions, outstanding observed quantity, source refs and explicit
UC-07/08/09 admission gaps. It supports stock and option executions without
inventing PUT/CALL or covered-call classification. It also hardens existing
structured retrieval independently of external providers. No schema/persistence
or default synthesis policy changes are necessary.

## Acceptance boundary

Regression/fixtures prove code behavior only. The focused runtime validation will
check the new projection and strict-history cutoff through `/history/context`
without provider/model calls. No PASS for complete lifecycle, historical learning,
calibrated assignment, full workspace replay or real latency is claimed.

## Implemented block and validation

- Existing SQLite read adapter now reuses OperationReconstructor directly, without
  invoking OutcomeEngine for an unverified execution sequence.
- The derived `ObservedLifecycle` contract exposes increases, partial reductions,
  net-flat/outstanding observed deltas, dates, cash flows and source refs. Uses
  original source quantity units. Details are bounded to ten sequences and twenty
  movements/source IDs per sequence; omission counts are explicit. Summary totals
  still include all admitted rows, including pre-window legs needed for a sequence.
- The existing history payload carries the UC-07/08/09 admission requirements,
  unknown-outcome count, zero *admitted* outcomes and null similarity confidence.
  No active learning, frequency or ranking effect is generated from these rows.
- PersonalHistory renders the detail through the existing common AnalysisOutput
  in Opportunities, Strategy Lab and Copilot. No independent history screen or
  financial calculation is added to React. Older backend payloads still render.
- `experience-ranker-v3-pit-admission` rejects future/provisional/invalid outcomes,
  future exit snapshots, future learning versions/confirmations/evidence, expired
  validity and unrelated subjects. Unresolved semantic references do not become
  canonical learnings. PRE-ANALYSIS filters the actual learning objects exposed
  to agents, not only their rank. Supporting/contradicting lifecycle handling stays.
- `learning-engine-v2-outcome-admission` refuses unknown/nonfinite P&L, future or
  provisional outcomes and duplicate experience/operation/outcome identities.
  Unknown P&L cannot become a losing observation or increase sample confidence.
- No new table, canonical ledger, ingestion, order, provider call, background model
  dependency or default synthesis-policy change is introduced.

Local checks: **718 Python tests PASS** under Python 3.14.7; **React TypeScript/Vite
build PASS**; `git diff --check` PASS. Fixture tests include partial repurchases,
stock reductions, same underlying units, strict availability, bounded detail,
broker isolation, unknown starting balance, prohibited outcome finalization,
future/unknown/provisional P&L, duplicate samples and unresolved semantic candidates.
GitHub CI must independently confirm the published HEAD. Visual desktop and Ubuntu
production acceptance are pending; fixtures do not validate personal performance.

## One focused Ubuntu gate after CI green

```bash
cd /opt/b3-investment-options-agent && \
git pull --ff-only origin feature/react-functional-v43-integration && \
sudo systemctl restart b3-runtime.service && \
./.venv/bin/python scripts/validate_personal_history_real.py --check-observed-lifecycle
```

The script waits for readiness, checks ALL/PETR4/VALE3/RENT3 retrospective and
strict-history queries, and prints sources, observed sequence detail, exclusions
and admission status. No OPLAB/LLM request, source discovery or reingestion.
Its PASS is explicitly scoped to observed read projections and the history cutoff,
not complete UC-07/08/09 or a whole-workspace historical replay.

## Updated matrix / remaining next steps

| Capability after this block | Classification | Remaining gate |
|---|---|---|
| Partial execution movement / bounded observed lifecycle | fully implemented in read projection | Ubuntu gate above |
| Contextual lifecycle detail | frontend-only gap resolved in build | Desktop visual E2E remains open |
| Canonical outcome/learning admission safeguards | fully implemented in existing engines/services | Production structured loaders remain implemented but not wired integrally |
| Final assignment, expiry, complete roll-chain economics | missing implementation + missing real data | Independent settlement / identity / opening-balance evidence |
| Persistent UC-08 POST-OUTCOME / qualified UC-09 cohorts | implemented but not wired integrally; canonical runtime commit/idempotency missing | No activation from observed sequences |
| Complete account history and entry features | missing real data in examined stores | Reconcile actual batch origin/status; do not repeat directory discovery |
| OPLAB / full synthesis latency | missing real access/measurement | External gate remains open; independent work continues |

Next: obtain new evidence identifying the complete note batch (source location or
existing import receipt/status) rather than searching the same directories. Then
qualify lifecycle and PIT entry snapshots with the existing contracts before
canonical finalization, persistence and POST-OUTCOME activation. Without those
inputs, no source-linked comparable outcomes or assignment rates are announced.
The independent performance/UI follow-up remains shared context reuse and
deterministic-first Opportunities/Strategy Lab without duplicate acquisition.

Limit: canonical domain contracts do not themselves carry full ingestion-history
proof. The new version/outcome timestamp checks are necessary gates; loaders must
still prove availability and canonical version ownership. They do not manufacture
an as-loaded record's availability at a historical cutoff.
