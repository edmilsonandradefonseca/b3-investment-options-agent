# Canonical Experience/Learning boundary — 2026-10-02

## Authority and pre-code matrix

Restart/handoff, ADR-0020/0021, approved UC-07/08/09 and frozen V4.3 remain
binding. GitHub HEAD `83e93d5`, PR #66 open/draft and CI #1277 SUCCESS verified.
The completed Ubuntu gate at `53c5682` is not repeated. Production has 264
execution observations; zero eligible outcomes remains the accepted state.

| Area | Before this block | Selected additive work |
| --- | --- | --- |
| Execution read projections / exact candidate binding | Fully implemented, focused Ubuntu PASS | Preserve unchanged |
| Canonical learning/ranking algorithms | Implemented | Reuse typed domain objects |
| POST-OUTCOME commit-before-projection / replay | Missing implementation | Require injected canonical atomic store boundary and validate receipts |
| PRE-ANALYSIS runtime service composition | Implemented but not wired by runtime configuration | Explicit trusted typed service parameter |
| Canonical experience presentation | Frontend-only gap | Shared sample/confidence/support/contradiction view |
| Production canonical outcome/learning persistence adapter | Missing implementation and actual store ownership proof | Remains blocked; no convenient table/ledger |
| Verified terminal/account evidence and entry PIT snapshots | Missing real data | No admission from notes/current metadata |

No structured Operation/Outcome/Learning persistence adapter exists in the
repository composition. The existing projection ledger records rebuildable
memory status only; Qdrant/Neo4j must not be promoted to canonical authority.
The implementation therefore defines an injectable storage contract, not a
replacement database. A production adapter must use the actual canonical owner
and atomically commit Experience/Learning/event identity with concurrency checks.
Until that adapter and verified source facts exist, POST-OUTCOME stays disabled.

## Intended boundary

Validate exact OutcomeFinalized identity, immutable input fingerprint, operation
links, entry-time snapshot and final valid outcome. Load an already committed
event result before computing any learning. Fresh results require an atomic
commit receipt; only then may rebuildable projections run. Replays reuse the
committed learning version, including retries after projection failure, without
adding a sample or aging/updating the learning again. Conflicting payloads under
the same event identity and optimistic-concurrency conflicts must be rejected by
the canonical owner. Tests use explicit fake owners only; these are not runtime
fallback stores.

PRE-ANALYSIS must expose only the configured typed canonical service result,
with unavailable states for missing loader or typed snapshot/regime. Serialized
request fields cannot supply canonical learnings or assessment. Shared UI shows
available learning versions, sample size, confidence, provenance and supporting
and contradicting evidence without modifying investment ranking.

## Completed implementation and verification

- POST-OUTCOME requires a `CanonicalPostOutcomeStore` supplied by the canonical
  owner. Missing configuration fails before learning or projection. The typed
  receipt binds event/version/time, immutable input fingerprint, exact Experience
  and commit timestamp. Learning receipt checks preserve event-time version,
  evidence membership and statistical sample consistency.
- Entry snapshots must represent the actual operation entry timestamp and belong
  to its underlying/instruments; optional operation snapshot/outcome links must
  match. Current features cannot be relabeled as historical entry evidence.
- The owner must atomically enforce event/economic identity uniqueness and CAS
  against `expected_previous`. No store implementation or new ledger is added.
  Replays reuse the original committed result and retry deterministic projections
  without another LearningEngine invocation. Failed commits cannot project.
- `configure_default_workflow(experience_context_service=...)` now accepts the
  actual typed PRE-ANALYSIS service. It does not deserialize HTTP context into a
  canonical service or create empty fake stores. Loaders must prove actual
  commit/ingestion availability at the analysis cutoff; domain finalization and
  update times alone are insufficient for historical availability.
- PRE-ANALYSIS executes before agents even when unavailable, exposing the reason
  and clearing untrusted request learning/assessment fields. Missing typed
  snapshot/regime remains unavailable. ISO timestamp cutoffs are respected rather
  than silently replaced with the snapshot time.
- The shared Opportunities/Strategy Lab/Copilot analysis shows canonical sample,
  confidence, lifecycle, supporting/contradicting evidence, regime/validity,
  population bias, model/schema and provenance when the trusted service supplies
  them. Presentation bounds learnings/evidence/source details to 20 and reports
  omissions. Default and deterministic-only paths explicitly report an
  unconfigured canonical loader; observation eligibility and ranking are unchanged.

Verification: **757 Python regression tests PASS**, TypeScript/Vite build PASS.
Tests include commit ordering/failure, receipt conflicts, replay without sample
growth, projection retry after canonical commit, future learning rejection,
terminal/PIT links, runtime typed injection, forged JSON rejection and real typed
service-to-agent/presentation payloads. All happy learning examples in these tests
are synthetic fixtures, not claims about the user's operations.

## Additional Ubuntu evidence supplied during this block

The user's terminal attachment confirms `83e93d5` installed and the existing
observed-lifecycle validator PASS with the now loaded batch. ALL: 264 executions,
129 observed sequences, zero eligible outcomes; strict validation-time read also
264 executions and reports eight rows with unknown intraday ordering. PETR4 root
association: 17 executions / nine sequences; VALE3 and RENT3 root associations:
one execution / one sequence each. These are explicitly unverified option-root
associations, not confirmed stock identity or final operation outcomes. All
sources are untruncated; the earlier single-execution snapshot is superseded.

No repeat of the completed validators is requested. Production outcome admission
still requires verified coverage/opening balances, terminal settlement/linked
roll sources, immutable entry snapshots/regimes and an actual canonical owner
adapter. Next work must establish that ownership from the runtime's existing
stores before implementing persistence. Qdrant/Neo4j and the projection-status
ledger remain rebuildable consumers, never substitutes for canonical storage.

The next Ubuntu evidence collection, after this complete block is published and
CI is green, is a schema-only read of exactly the three already known runtime
databases. This is not a directory scan or a repeat of execution-history tests.
It exposes no business row values, creates no missing database and cannot prove
canonical ownership automatically. The inspection script has regression checks
for byte preservation, unusual quoted table names and missing-directory safety.

```bash
cd /opt/b3-investment-options-agent && \
git pull --ff-only origin feature/react-functional-v43-integration && \
sudo systemctl restart b3-runtime.service && \
./.venv/bin/python scripts/inspect_canonical_learning_storage.py --data-dir /opt/b3-runtime/data
```

Review this schema evidence before selecting an existing canonical adapter or
proposing essential persistence. Do not load client JSON or graph/vector memory
as a convenient canonical fallback.
