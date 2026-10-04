# Economic backend acceptance and remaining closure gates — 2026-10-03

## Verified scope

User requested finishing four economic backend blocks before rebuilding the frontend. The implemented economic kernel and bounded asynchronous pipeline are accepted on Ubuntu. This is not full FRONTEND_FUNCTIONAL_SPEC/AC01–28 acceptance or complete broker data acquisition.

| Block | Backend implementation | Remaining scope |
|---|---|---|
| 1 Dividends | Background collector, existing Qdrant snapshots, stored-only BUY/Opportunities reads, explicit dates/sources and paid/announced separation | BBDC4 provider returns unavailable; forecasts remain UNKNOWN |
| 2 Institution targets | Qualified existing-store reader, reviewed XP ingestion, periodic primary-domain discovery, separate Qwen evidence worker | BTG/Safra/Itaú factual acquisition layouts not validated; candidate URLs are not admitted targets; XP HTTP restrictions remain |
| 3 Economic decision | BUY×BUY, conditional target potential, explicit user scenarios, income/sizing/cash/risk/portfolio effects and Opportunities integration | No unsupported expected returns or calibrated assignment probabilities; qualitative expert scoring not claimed |
| 4 Validation/activation | CI, actual Ubuntu, senior regression, active HTTP and installed production consumer accepted | New React frontend visual acceptance remains its next phase |

## Gates and observed results

Code checkout 80194eca4772534ce01fbac964efac7f336992c9 installed in /opt/b3-investment-options-agent. CI 37167071293 PASS; 908 local tests passed. Ubuntu 37167068552 PASS: portfolio/watchlist universe 30 assets; actual discovery found five unsupported-layout candidates and one source not admitted. No search snippet became a target fact. Isolated actual Qwen queue drained two consecutive batches: processed 2, READY 2, remaining 0, elapsed 50.3591 seconds. Economic senior 82.0488 seconds and Opportunities senior 91.8347 seconds, two canonical assessments each; structural regression, not expert superiority.

Active HTTP/installed-worker workflow 37167525790 PASS on validation commit 09d890744fc1057e2cb09071ca205cb5de1a629f. BUY 1.6964 seconds, economic decision 1.3181 seconds, sourced Opportunities 1.4247 seconds, zero LLM calls, cash conservation and STORED_ASYNC_SNAPSHOT origins. API was already authenticated-restarted by user before the background-only reliability increment. Final code changes affect separately invoked producer/consumer scripts; no new financial HTTP route contract was introduced. Generic workflow's noninteractive API restart attempt was blocked and is not claimed successful.

Installed systemd consumer ExecStart confirmed to point to the updated checkout script. Actual bounded production CLI batch processed 1 READY, failed/degraded/deferred 0, worker_busy false, remaining queue 7. Batch consumed approximately 366 seconds including process overhead. This proves installed production consumption, not 23-second latency for all dossier types or an empty backlog. Nightly producer and local analyst timers observed active. Sequential draining is bounded to 20 batches, 1800 seconds plus at most one in-flight request. Runtime failures back off and stop at three attempts; abandoned RUNNING requests become eligible after a 20-minute lease; concurrent claims are locked. Pending items are retained for following executions.

## Current role and configuration

Qwen3 4B Instruct 2507 Q4_K_M is the auxiliary asynchronous dossier worker, configured through B3_LOCAL_EVIDENCE_MODEL. Context 4096, output cap 2048, temperature 0, timeout 600. Canonical financial calculations remain Python; senior financial interpretation remains the B3 specialist/OpenClaw flow. Global model configuration and João routing unchanged. Per-request reference-constrained structured generation and strict admission remain mandatory.

## Remaining work before claiming integral completion

1. Validate primary report acquisition layouts for BTG/Safra/Itaú against accessible complete documents with explicit publication/version dates and horizons. Never infer missing horizons from aggregate target pages or bypass source restrictions.
2. Score dossier semantic accuracy and sustained backlog throughput across ordinary portfolio/news/dividend bundles; one installed batch and two short reports do not establish all workload quality/capacity.
3. Rebuild frontend from docs/FRONTEND_FUNCTIONAL_SPEC_V1.0.md and docs/DECISION_WORKSPACES_DELIVERY_PLAN_2026-10-02.md; visual acceptance requires the replacement interface. No new frontend was produced in this backend increment.
