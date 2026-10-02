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

## Real SQLite schema evidence — 2026-10-02 12:09 America/Sao_Paulo

The user supplied the terminal output after installing `2104696`, restarting
the runtime and running the known-SQLite inspector. All three files READ_OK,
all table inventories untruncated, no business rows read. This gate is complete.

| Known owner | Confirmed schema role | Outcome/Learning authority conclusion |
| --- | --- | --- |
| options.sqlite3 | option_transactions with source IDs, fingerprint and execution economics | Existing execution owner; no final economic outcome contract |
| source_manifest.sqlite3 | source_manifest with import/coverage/scope/completeness fields | Source availability/provenance; no final outcome or learning version |
| b3_agent.db | 11 tables: instruments, transactions, capital_profile, sources/ingestion, dataset registry, claims/source links, retrieval traces and usefulness attribution | No dedicated Operation/Outcome/FeatureSnapshot/MarketRegime/Learning tables in this file |

Claims and evidence links can represent sourced claims; their presence is not a
canonical Learning with statistical sample, strategy/regime/PIT snapshots and
atomic OutcomeFinalized replay. Retrieval traces and usefulness attribution
cannot supply the missing numerical truth. Do not overload them as a convenient
hidden learning ledger.

The SQLite-only inspection does **not** prove there is no canonical Parquet
storage: `dataset_references` exists, and no registry records were read in the
completed gate. The updated matrix is therefore: known SQLite schemas fully
inspected; declared dataset ownership missing real metadata; production adapter
still missing implementation; terminal/PIT outcome facts still missing real data.

The inspector now has a separate `--registered-datasets` mode. It reads only
registry metadata from b3_agent.db, then schemas of explicitly registered Parquet
files inside the supplied data directory. It does not repeat the three-file
schema inventory, scan registered directories, follow paths outside that scope,
read Parquet business rows or infer eligibility from column names. Empty/stale
registries remain explicit; they do not prove global absence of storage.

Verification for this focused addition: **760 Python regression tests PASS**;
no React code changes. Tests prove no business values are exposed, DB/file bytes
are preserved, registry limits are reported and directories are not scanned.

After publication and green CI, run the new metadata gate once:

```bash
cd /opt/b3-investment-options-agent && \
git pull --ff-only origin feature/react-functional-v43-integration && \
./.venv/bin/python scripts/inspect_canonical_learning_storage.py --data-dir /opt/b3-runtime/data --registered-datasets
```

No service restart is required for this schema-only script/docs addition. Do not
repeat the completed lifecycle, exact-history or known-SQLite schema checks.
