# Brokerage batch reconciliation — 2026-10-02

## Authority and pre-code decision

Verified branch HEAD a0d0a2f; PR #66 open/draft; CI #1272 SUCCESS.
The user confirmed a0d0a2f installed with both observed-history PASS markers,
then supplied a brokerage-note ZIP and authorized processing to reconcile
missing executions. The restart/handoff and their architecture, use-case,
traceability, frontend and deterministic/PIT authorities remain unchanged.
No production directory discovery or OPLAB diagnosis is repeated.

| Capability before this block | Classification | Smallest additive action |
|---|---|---|
| Existing PDF/ZIP -> option ledger and source manifest | fully implemented, real parser coverage incomplete | Extend real BTG execution row formats |
| Blank share class / day trade observation D | missing implementation | Accept source rows without inventing contract identity |
| Identical distinct fills within a note | missing implementation in deduplication | Preserve multiplicity in existing fingerprint index |
| Batch completion notice | frontend-only gap | Show processed/refused counts rather than generic completion |
| Runtime source reconciliation | missing real data | Supplied batch now available for isolated audit; Ubuntu import pending |
| Full UC-07/08/09 outcomes and PIT entry features | missing implementation + missing real data | No canonical outcomes/learning synthesized from executions |

## Real source audit and implementation

The supplied ZIP contains 156 PDFs, 131 distinct byte fingerprints.
Before correction: 143 processed, 13 refused, 581 parsed row occurrences across
copies and 243 ledger rows. The option-only parser silently missed 71 option
row occurrences, including repeated copies: blank ON/PN classes and D day-trade
observations were not recognized. Some notes could thus be partly imported.
A second issue collapsed two identical-valued but distinct fills in one note.
Visual source review confirmed the execution layout and separate fill rows.

The parser now accepts those formats. It retains every previously recognized
row's legacy transaction ID and uses a separate additional-row namespace for
newly recognized rows, preventing shifts/collisions with installed history.
Unsupported option rows reject the entire note before ledger writes, preventing
silently incomplete ingestion. ON/PN and D are not used to infer position,
contract settlement, covered calls, rolls or economic outcomes.

Ledger append retains the original first economic fingerprint; further distinct
occurrences within a supplied brokerage note use deterministic occurrence
fingerprints. Repeated copies remain idempotent. Snapshot ingestion behavior is
unchanged. Legacy rows receive the compatible first fingerprint before additional rows, even
when a newly recognized equal-valued fill precedes them in the PDF. Recovery
was verified in the previously partially imported audit ledger (264 total,
then zero inserted on repeat). No new ledger/table or destructive overwrite is introduced.
The frontend completion notice exposes processed/refused PDF counts and, for
ZIP batches, inserted execution count; per-file JSON remains available.

## Audit result and validation

Corrected existing ingestion service, isolated data directory:

- 144 PDF files processed, 12 refused; 652 parsed occurrences across copies.
- 61 unique supported option notes; 264 executions including distinct equal fills.
- Execution dates: 2026-04-30 through 2026-10-01.
- All copies/variants of each supported note have identical economic row multisets.
  Their independent per-note total is exactly 264, matching persisted rows.
- Reimport of the same ZIP: zero inserted executions.
- Existing Ubuntu execution ID/economics is present unchanged in the batch.
- Read-only history: ALL 264 executions / 129 observed sequences; PETR4 root 17
  executions, VALE3 root 1, RENT3 root 1. Root identity remains unverified where
  only the option prefix is available. Eight rows have ambiguous intraday ordering
  and are excluded from lifecycle reconstruction, not erased from source history.
- Twelve refusals: eight stock-market PDFs (including copies), three rental PDFs,
  one flexible-option exercise PDF. These are unsupported, not empty account history.
  The flexible source needs its own typed contract/settlement evidence before use.

Local validation: 722 Python tests PASS; React TypeScript/Vite build PASS;
git diff --check PASS. Regressions cover missing share classes, day-trade D,
unchanged legacy IDs, recovery into an existing ledger, repeated copies,
identical distinct fills and fail-closed unsupported option rows.
GitHub CI must independently confirm the published HEAD.

No private notes, account identifiers, raw rows, audit databases or archives are
published in GitHub. The isolated audit does not update the Ubuntu runtime.

## Deployment / next gate

After CI is green, update the existing branch and restart b3-runtime.service.
Use the existing frontend import control (pointing to the Ubuntu runtime) to
upload the supplied original ZIP. No replacement database or manual SQL is needed.
If the active option ledger still contains exactly the single previously observed
execution, expected inserted_count is 263 and final row count is 264. Other valid
existing data may change inserted_count; preserve it and inspect the receipt.
Expect 12 explicit unsupported-file refusals; do not claim the entire mixed batch
was imported. Repeating this ZIP must insert zero further option executions.

Then run the existing observed-lifecycle validator once against the populated
runtime. Its PASS remains scoped to the projection and PIT admission.
Imported_at is the actual import time, not the trade date: loading old notes now
does not prove availability at historical entry. Completeness, opening balances,
terminal settlement, full roll chains, fees and PIT features remain UNKNOWN/open.
Next additive source work is stock/rental/flexible evidence in the existing
canonical contracts, followed by qualification; no new convenience ledgers.
