# B3 Backend Production Readiness Gate — 2026-09-28

**Status:** NOT YET READY — CI GREEN; runtime blockers remain  
**Architecture:** V4.0 frozen + V4.1 additive runtime routing  
**Branch under validation:** `fix/b3-openclaw-runtime`  
**Frontend rule:** do not resume frontend work until this gate is READY.

## 1. Definition of READY

The backend is READY only when all blocking gates below are green on the real Ubuntu runtime.

### Blocking gates

1. **Full regression**
   - full `pytest` suite passes in a clean code-default environment;
   - production environment overrides must not contaminate default/config tests.

2. **Shared runtime**
   - embedding service healthy at 768 dimensions;
   - Qdrant hybrid collection healthy;
   - Neo4j connectivity healthy;
   - canonical portfolio snapshot loads;
   - BRAPI/OPLAB real providers work;
   - macro provider works;
   - no service ownership conflict with João.

3. **UC-01..UC-12 functional acceptance**
   - zero FAIL;
   - LIMITED is acceptable only when caused by explicitly missing real historical observations/corpus, not missing code;
   - every LIMITED condition must be identified and visible to callers.

4. **Fast Router HTTP E2E**
   - deterministic Portfolio/Options/Risk paths return HTTP 200 without Luna;
   - explicit stress executes deterministically;
   - ambiguous/complex intent escalates to OpenClaw;
   - direct paid OpenAI API fallback remains disabled by default.

5. **AI runtime**
   - local DeepSeek runtime smoke passes;
   - isolated `b3-investment` OpenClaw/Luna smoke passes;
   - no 429/quota/paid-API dependency in normal production path.

6. **Persistence / historical intelligence**
   - canonical transaction ledger path is known and writable;
   - imported brokerage-note history is visible to UC-07;
   - UC-08/09 may remain LIMITED when there are insufficient finalized outcomes/experience, but not because ingestion/persistence is disconnected.

7. **Operational jobs**
   - macro refresh timer enabled and healthy;
   - UC-10 nightly timer enabled and healthy, or explicitly disabled by an approved operational decision;
   - nightly job is bounded and may skip when no fresh/material evidence exists.

8. **Observability / error behavior**
   - health endpoint returns OK;
   - no uncaught traceback during gate;
   - no 429/insufficient_quota/credit_balance_exhausted;
   - HTTP analytical errors do not falsely mark backend connectivity offline;
   - deterministic/LLM route target is visible in audit/result metadata.

## 2. Current verified evidence

Verified on the real Ubuntu runtime:

- real portfolio: 47 positions / 24 economic exposures;
- UC-01 PASS;
- UC-02 PASS;
- UC-03 PASS;
- UC-04 PASS;
- UC-05 PASS;
- UC-06 LIMITED due insufficient persisted multi-factor real history;
- UC-07 LIMITED because no canonical transaction rows were visible;
- UC-08 LIMITED due insufficient finalized outcomes;
- UC-09 LIMITED because the real experience corpus has not accumulated;
- UC-10 PASS with hybrid evidence corpus;
- UC-11 PASS on explicit real-portfolio stress;
- UC-12 PASS with prohibited execution actions enforced;
- overall UC acceptance: 8 PASS / 4 LIMITED / 0 FAIL;
- Fast Router HTTP: UC-01, UC-02 and UC-11 paths passed;
- local DeepSeek runtime passed;
- OpenClaw/Luna transport passed;
- no 429/quota/Traceback/ERROR during the HTTP service validation window;
- macro refresh timer enabled;
- João scheduler intentionally inactive during B3 validation.

## 3. Remaining blockers before READY

### B1 — full regression / CI

**Code-side status: GREEN.** GitHub Actions CI run #999 completed successfully after correcting the read-only diagnostic test false positive. The Ubuntu full gate must still be rerun with the corrected clean-environment ordering to record host-local evidence.

### B2 — reconcile canonical transaction ledger

Production acceptance reported:

`OPTION LEDGER WARNING no options.sqlite3 yet`

This is material because UC-07 consumes the canonical execution ledger. Determine whether brokerage-note data:
- was never persisted;
- was persisted to another historical path;
- was imported before the current canonical runtime path;
- or requires re-import into the canonical runtime data directory `options.sqlite3`.

Do not make UC-07 PASS by fabricating transactions.

### B3 — UC-10 nightly operational state

The installer has been corrected so both nightly intelligence and macro refresh load the canonical B3 runtime environment files (`/etc/b3-runtime.env` and `/opt/b3-runtime/b3.env`) in addition to the shared platform environment. The Ubuntu units still need to be reinstalled/enabled and verified by the full gate.

## 4. Non-blocking calibration/data maturity items

These do not prevent backend READY when the engine correctly reports LIMITED/uncertainty:

- UC-06 needs enough real synchronized multi-factor observations for calibrated studies;
- UC-08 needs sufficient finalized operation outcomes;
- UC-09 needs an accumulated real experience corpus;
- UC-03 currently reports `rejected=0`; review opportunity-filter/ranking calibration before treating the full ranked set as decision-ready.

## 5. Final release criterion

The backend may be declared:

`BACKEND PRODUCTION READY FOR FRONTEND INTEGRATION`

only after:

- corrected full gate: 0 blocking failures;
- B2 ledger path is reconciled and tested;
- B3 nightly operational decision is completed;
- all remaining LIMITED states are demonstrably data-maturity conditions rather than disconnected implementation paths;
- PR #61 validation evidence is recorded.

No architecture V4.0 redesign is required.
