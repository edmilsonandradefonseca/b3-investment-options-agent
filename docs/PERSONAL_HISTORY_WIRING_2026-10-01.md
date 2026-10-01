# Personal history wiring — additive implementation

## Real data gate completed

The user's second diagnostic confirmed the active B3 uvicorn process uses `/opt/b3-runtime/data`. The bounded project/runtime/backup discovery completed with no truncation/errors, finding one execution in each of two ledgers (the same identity), zero manual transactions, no source manifest and no brokerage PDFs/ZIPs in the searched directories. It found portfolio XLSX inputs only. No conclusion of system-wide data loss is justified. Full historical outcome validation remains blocked by missing source coverage; implementation is not blocked.

## Implemented block

- `PersonalHistoryService` reads existing `option_transactions`, `transactions` and `source_manifest` through SQLite read-only/query-only snapshots. Constructors/migrations are not invoked. No new tables or persistence.
- Reuses existing `Transaction` and `HistoricalOperationsService`. Source direction, original units and cash flows preserved; broker isolation, day-level ordering ambiguity, crossed quantities, invalid amounts and potential cross-ledger duplicates are explicit exclusions.
- A net-flat execution sequence is labelled `OBSERVED_NET_FLAT_SEQUENCE`, with unknown economic outcome and unverified zero opening balance. This is not a finalized learning outcome. A lone buy may be a closing trade, not an opening position.
- Dates without times retain DAY precision and no claimed execution timestamp. Explicit `as_of` activates strict availability filtering; without known availability, records cannot enter historical replay. Default mode is explicitly retrospective as loaded.
- Underlying-prefix matches are `UNVERIFIED_OPTION_ROOT`; they cannot prove PETR4 identity, coverage, expiry or strike. No ticker-suffix assumptions are promoted.
- Source coverage, assignment/expiry/roll frequencies, IV/regime comparison and validated similarity remain UNKNOWN/null. Zero learning sample means zero validated outcomes admitted, not zero assignments or losses.
- History injected before reasoning inside existing LangGraph; current portfolio snapshots reload per invocation. Workspaces carry source-linked personal history in deterministic context. Specialists receive that slice too.
- `GET /history/context?ticker=PETR4&since=2026-04-01` returns bounded context without models/providers or initialization. `as_of` requires a timezone-aware timestamp.
- Workspace `/orchestrate` supports `context.analysis_mode="deterministic"`: canonical result/context returned with `derived_synthesis_status=NOT_REQUESTED`, no João/model calls. This is an API capability; automatic two-stage React loading is not part of this commit.
- Model-produced result keys cannot overwrite top-level deterministic workspace result keys when responses are merged.

## Performance

- Read snapshot reuse is bounded/process-local with SQLite/WAL revision invalidation, content fingerprints, copy isolation and singleflight. No durable cache table.
- Model reuse is bounded/process-local for exact complete input, instructions and schema in one client/model instance. No timestamp stripping or cache reuse across changed facts. Failures/incomplete structured outputs are not cached. Whitespace-only structured prompt compaction preserves evidence.
- Stage latency and model cache/input/output-size telemetry exposed. No claimed production speedup until measured.
- `B3_WORKSPACE_SINGLE_SYNTHESIS=true` enables one senior reasoning call for workspace requests inside LangGraph, preserving canonical context/history, retrieval and downstream RiskValidator. Default full specialist path is retained for quality comparison.
- `B3_JOAO_SYNC_PERSPECTIVE=false` omits an extra synchronous João synthesis while retaining João memory retrieval. Existing default remains compatible.
- DeepSeek remains asynchronous; no router change and no autonomous trading.

## Remaining scope

This block does **not** claim completed UC-07/08/09. Verified expiry/assignment/roll chains, persistent outcome-driven learning, PIT feature/regime reconstruction and calibrated similarity need canonical evidence and further additive wiring. No fabricated FeatureSnapshot/MarketRegime or synthetic ACTIVE learning is inserted to make tests pass. Canonical strike/expiry selection, full economic ranking, cross-provider context reuse and frontend historical drill-down also remain separate work. Exact-input LLM caching does not imply reuse when changing acquisition timestamps/context make requests different.

## Focused real acceptance

After the CI-green update/restart, run `scripts/validate_personal_history_real.py`. It reads the running API for ALL/PETR4/VALE3/RENT3, validates null lifecycle frequencies and reports source counts/telemetry. It does not invoke senior reasoning, ingest notes or validate a historical win rate.
