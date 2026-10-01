# Decision intelligence review — 2026-10-01

## Evidence boundary and checkpoint

Reviewed integration HEAD `99d860a524cdc6b6cf4135695bfb5973f4c6e91a`, PR #66 open/draft, CI #1260 SUCCESS. Read the six required checkpoint/prompt/architecture/UC/traceability/frontend documents and Architecture V4.0 / ADR-0020. Older MISSING labels in traceability are historical; its reconciliation section supersedes them.

The review environment is **not the Ubuntu runtime**: `/opt/b3-investment-options-agent` is absent. No actual SQLite rows have been inspected. All production counts, date coverage, source completeness and historical feature availability remain **UNKNOWN**, not zero or absent. No financial implementation or persistence change is justified by fixture data alone.

The statement above records the initial review boundary. The user subsequently supplied real diagnostic output; the updated evidence is recorded below.

## Pre-implementation matrix

Classification is per capability, not a claim of full UC acceptance.

| Capability | Classification | Code evidence / remaining gate |
|---|---|---|
| Brokerage option side/price representation | fully implemented | `options/brokerage_notes.py`: C -> positive quantity/cost, V -> negative; `average_cost` is execution price. Does not mean quantity is contracts x 100. |
| Note ingestion into existing ledger + source manifest | fully implemented | `options/brokerage_batch.py` writes `options.sqlite3/option_transactions` and `source_manifest.sqlite3`; real coverage unverified. |
| Generic execution reconstruction and closed cash-flow outcome | fully implemented | `experience/operation_reconstruction.py`, `outcome_engine.py`: net-zero closes, source transaction IDs retained. Limited scope, not complete option lifecycle. |
| Brokerage ledger -> UC-07 input adapter | missing implementation | UC-07 accepts `Transaction` objects; ingestion produces `OptionTransaction`. Need read adapter, no duplicate ledger. Resolve overlap with user-entered `transactions`, never concatenate blindly. |
| UC-07/08/09 high-level service facades | implemented but not wired | `historical_operations.py`, `continuous_learning.py`, `historical_similarity.py` exist, but no production call sites found for these facades. |
| PRE-ANALYSIS structured experience | implemented but not wired | `orchestration/workflow.py` accepts optional `ExperienceContextService`; `orchestration/runtime.py:configure_default_workflow` does not pass it. Hook also requires typed FeatureSnapshot and MarketRegime. |
| POST-OUTCOME learning | implemented but not wired | `orchestration/experience_workflow.py` implements service/graph; brokerage ingestion does not invoke it. Finalized outcomes, canonical persistence and idempotency must precede projections. |
| Expired OTM, assignment, exercise, linked/partial rolls | missing implementation | Reconstructor emits only OPEN/CLOSED. Outcome engine accepts additional terminal statuses but does not establish their evidence. No chain reconstruction in this path. |
| Historical broker counts / PETR4 / PUT/CALL coverage | missing real data | Means missing **review access**, not missing user records. Collect PRAGMA, counts, ranges, sign distribution, safe representative rows and manifest completeness first. |
| Entry IV/Greeks, regime and covered-call state | missing real data | Runtime availability UNKNOWN. Current holdings or current IV cannot establish past coverage or IV. PETR option prefix alone cannot prove PETR4 underlying, expiry year or strike. |
| UC-03 live economic ranking | missing implementation | `opportunity_live.py` explicitly defers incomplete valuation/risk/portfolio/liquidity/experience ranking. Keep deferred until comparable canonical inputs exist. |
| UC-04 historical context | implemented but not wired | `strategy_comparison.py` supports experience confidence deltas; live workflow does not load personal UC-07/08/09 evidence. |
| UC-12 structured history rationale | implemented but not wired | Agent context supports experience fields; production composition does not supply structured retrieval. Semantic memory alone cannot replace execution history. |
| Contextual precedent/history drill-down | frontend-only gap | Backend result presentation belongs in existing workspaces/Copilot, no new top-level screen. Only implement after backend returns bounded typed evidence; most current omissions are backend gaps, not UI-only. |
| Cross-workspace context/senior reuse and stage telemetry | missing implementation | Existing provider caches and optional supplied asset-evidence reuse do not cover complete context/senior result reuse. |

## Reconstruction possible without changing schema

Subject to actual rows and provenance: source-linked signed option executions, trade cash flows, exact-symbol closed/open sequences, partial reductions, counts by period/type and known gross closing results. Use `average_cost` and source `total_cost` consistently and report discrepancies. Do not multiply imported quantities by an assumed 100.

`transactions` uses explicit BUY/SELL + positive quantity/price; `option_transactions` uses signed quantity/cost. The former repository defaults to 100 rows, unsuitable for complete history without an explicit unbounded/paginated read. Reconstructor groups by ticker, not account, and rejects sign-crossing executions; this must not merge brokers or discard unsupported records. Same-day note IDs do not prove execution ordering.

Contract identity/expiry/strike/type require canonical metadata and availability checks. A diagnostic symbol-letter histogram is only a **symbol convention hint**, never a lifecycle or underlying mapping. Expiry date in the past does not prove worthless expiry. A repurchase and another sale do not prove a roll. Complete chain economics require linked quantities, predecessor/successor evidence, fees where available and separation of stock-delivery economics. Unknown fees mean gross result only. Unknown terminal outcome stays UNKNOWN and must not contribute a zero/false assignment observation.

Personal assignment/expiry/roll frequencies must expose numerator, eligible known-outcome denominator, excluded/unknown counts, sample confidence, coverage and selection bias. They are not market probabilities. IV/regime comparison is unavailable without PIT entry snapshots; never backfill those with today's observations.

## Latency review (static, not measured production attribution)

`server.py:_workspace_intelligence_response` builds context with `include_joao=True`, then invokes B3. `workspace_context.py` can collect per-ticker research, broad-market research and a synchronous João perspective. Production B3 configures three specialists, synthesis and final reasoning. Specialists fan out in LangGraph; they are **not three sequential calls**, but synthesis and final reasoning are downstream stages. Up to six model calls including João are configured. `OpenClawStructuredClient` starts a subprocess and fresh session for each call; no reusable result cache is present there. The reported 80–95s is user/runtime history, not a new measurement.

Smallest safe optimization after baseline telemetry:

1. Measure acquisition, SQLite/history, context, João, each specialist, synthesis, final reasoning, validation and total with monotonic clocks; report prompt/output size, invocation count and cache hit/miss/reason. Preserve timestamps and original observation provenance.
2. Reuse validated asset context separately from workspace presentation. Fingerprint domain/account, ticker/instrument, explicit as-of semantics, portfolio/capital revision, ledger/manifest revision, quote/chain timestamps and contents, evidence IDs/versions, feature/regime/learning versions and policy. TTL alone is insufficient. Refresh, corrected evidence or changed holdings invalidate reuse.
3. Cache derived synthesis separately with question/intent, alternatives/quantity/expiry, context fingerprint, model, prompt and schema versions. Bound size/TTL and coalesce in-flight identical requests; no cross-account reuse, no cached failures, no timestamp relabeling. Historical requests never reuse live context.
4. Compact structured slices with explicit omissions/source refs; deduplicate repeated evidence, preserve contradictions and UNKNOWN. Trial one senior synthesis over complete deterministic context inside existing LangGraph, with quality regression against full path; retain downstream RiskValidator. Do not simply bypass the authority workflow.
5. Return deterministic result first and expose separately requested/pending derived synthesis. DeepSeek stays background; no change to code-only router.

Additional review gates: workspace local dossier admission checks READY/quality flags but should reuse the exact-fingerprint/current selector; `senior.result` is merged after deterministic dictionaries in server, so protect authoritative key ownership in collision tests. These are code risks, not assertions that observed user data was contaminated.

## Smallest additive sequence

**Block A (this review):** repair/extend the existing historical diagnostic, which currently constructs repositories that initialize/migrate tables even when described as read-only. Use SQLite `mode=ro`, query-only, bounded read transactions and safe column allowlists. Produce all runtime evidence in one command. No new tables, ingestion, migration, runtime restart or LLM calls.

**Block B (after actual diagnostic):** read-only source adapter and evidence-qualified reconstruction over existing stores; extend existing UC-07 lifecycle only for provable cases, retain unknowns. Connect typed PRE-ANALYSIS loaders to UC-03/04/12 and contextual market view; wire finalized POST-OUTCOME via existing canonical/projection boundaries. No new persistence by convenience.

**Block C:** shared context fingerprint/reuse, telemetry, bounded senior synthesis reuse, deterministic-first response, typed contextual UI. Apply to PUT, CALL and stock; close/hold/roll require canonical position and chain evidence. Validate invalidation, PIT, unknown outcomes, partial fills, broker isolation, conflicting metadata and no model invocation in deterministic path.

Runtime results are a prerequisite for Block B, explicitly required by the user. This review does not claim Block B/C implementation or reduced measured latency. Block A is a complete diagnostic gate so the user needs one runtime command, not a series of exploratory queries.

## Added acceptance: VALE3 expiry and strike selection

Compare one-week versus one-month PUTs using the same observed chain/as-of and explicit portfolio/capital objective. Resolve actual listed expiries rather than inventing a date. Candidate generation and feasible strike selection remain deterministic. Include bid-based premium, spread/volume/OI, effective acquisition price, assignment capital, DTE, downside/stress, events within each horizon, IV/Greeks where available, personal comparable outcomes and confidence/coverage. Annualized premium alone cannot select the winner; missing liquidity/risk inputs keep ranking deferred.

Keep three distinct quantities: observed personal assignment frequency; model-estimated expiry ITM probability (with model, assumptions, timestamp and calibration limitations); early exercise/assignment risk. Delta is a sensitivity, not an authoritative assignment probability. A European risk-neutral expiry estimate is not a calibrated real-world probability or a full American early-exercise model. Missing validated probability inputs remain UNKNOWN. A best strike is conditional on an explicit objective and constraints; show trade-offs/Pareto alternatives where no defensible single winner exists. Reuse the same comparison contract for covered CALL and stock alternatives, retaining human decision authority.

## Real diagnostic received — 2026-10-01

The user ran the diagnostic from commit `80c3fd9` under sudo and supplied its output. This is actual runtime evidence, not fixtures:

| Inspected source | Observed result |
|---|---|
| `/opt/b3-runtime/data/options.sqlite3` | 1 dated/priced option execution, dated 2026-05-04, positive quantity; no PETR-prefixed symbols |
| `/opt/b3-investment-options-agent/data/options.sqlite3` | Same execution identity and fields as the runtime ledger; not a second independent operation |
| `/opt/b3-runtime/data/b3_agent.db/transactions` | 0 rows |
| `/opt/b3-runtime/data/source_manifest.sqlite3` | File absent |
| Direct `imports/brokerage_notes/*.pdf` in examined directories | 0 files |

These observations do not establish lost data, failed ingestion, full-host absence of notes, or complete history. The first diagnostic inspected only direct database files in selected directories; sudo changed the home candidate to `/root`. It did not verify the data directory in the running API process. Existing note-batch code archives PDFs and upserts a manifest, so the observed state differs from what a successful current batch at that path would normally produce; root cause remains UNKNOWN.

Matrix update: actual schemas/sign convention and the one row are now verified for these paths. Full personal history, PIT features and source coverage remain **missing real data in the inspected stores**, with storage-location/process mismatch still unexcluded. UC-07/08/09 wiring gaps remain independently confirmed in code. Do not compute assignment rates, covered-call outcomes or train learnings from this single unmatched execution. It may itself be a closing trade; it is not proof of an opening position.

The next coherent diagnostic block extends the existing script with `--discover --compact`:

- inspect the known runtime/service process tree and admit only a B3 uvicorn process;
- extract only B3 path variables, never credentials or unrestricted command/environment output;
- prefer the observed API data directory over configuration guesses;
- find the invoking user's project home under sudo;
- search bounded project/runtime/backup subdirectories for existing databases and PDF/ZIP/XLSX candidates, without parsing/importing/moving them;
- report truncation/read errors and preserve UNKNOWN coverage;
- replace misleading `CANONICAL_LEDGER_READY` with `CANONICAL_LEDGER_HAS_EXECUTIONS`, with explicit `history_coverage=UNKNOWN` and `lifecycle_acceptance=NOT_VALIDATED`.

No new canonical storage, model calls or financial inference is introduced. Source files and alternative databases must be located/reconciled before ingestion recovery or meaningful personal-outcome learning; no automatic copying from an alternative ledger is authorized by discovery alone.
