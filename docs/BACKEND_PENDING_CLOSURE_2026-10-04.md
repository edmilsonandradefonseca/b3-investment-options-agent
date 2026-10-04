# Pending backend closure — 2026-10-04

This checkpoint extends the earlier economic backend acceptance. It does not close the new React frontend or all AC01–28.

## Block 1, step 4: issuer dividend coverage

The background dividend producer now falls back to a bounded primary Bradesco RI acquisition when BRAPI fails for BBDC3/BBDC4. It follows the unique monthly notice linked by the issuer, reads its PDF, verifies the gross ON/PN amounts and the twelve declaration, record, ex-right and payment dates, and projects the result into the existing Qdrant snapshot collection.

The stored reader admits this exact primary source and parser. Coverage is explicitly `PARTIAL_MONTHLY_JCP_ONLY`; intermediate and complementary distributions are not claimed. Future scheduled declarations retain an unknown announcement date and do not authorize announced conditional income. No absence is treated as zero. HTTP403 upstream provenance is retained.

## Block 2, steps 3–4: target acquisition and local worker

Discovery and reviewed refresh now use bounded parsers for XP HTML, Safra single-equity analysis HTML, Itaú structured primary article/body and BTG primary PDF. Aggregate ticker pages, ambiguous classes, conflicting amounts, absent horizons and stale reports remain unadmitted.

Verified current factual records: XP ITUB4/BBDC4; Safra LIGT3 (BRL 4.20, 2026-12-31); Itaú VALE3 (BRL 94, 2027-12-31). Original report version/public acquisition dates and hashes are retained. Ubuntu acquired Safra live; Itaú returned HTTP403 and used the previously acquired reviewed record without redating it.

BTG parser validation uses a real MATD3 report. The report is accepted only at its historical point in time and rejected at the current cutoff for age. No current BTG fact is claimed. This is an explicit source coverage limitation, not a fabricated target.

The local worker prompt v7 bounds summary to 400 characters and each analytical list to two entries of 200 characters. Oversized outputs are marked degraded rather than silently truncated. The financial agent still receives canonical facts independently; structured admission does not certify every semantic claim.

## Observed verification

- Local suite: 916 tests pass.
- Worker v7 Ubuntu run 37168918244: one real target READY in 22.1 seconds; two isolated cases READY, no failed/degraded/deferred, queue empty.
- Expanded institution run 37169227243: four isolated reports READY in 108.9 seconds, four batches, queue empty; four primary records projected.
- Broad replay run 37169535475: one real dividend bundle, 10,456 input characters, READY in 160.1 seconds, 272 output tokens, 189 summary characters. News was absent from the pending queue; this run alone is not news acceptance.
- Installed consumer calendar was observed as `Mon..Fri *-*-* *:10/15:00`, not nightly-only.
- Expanded broad run 37169879958 passed both real bundle classes: dividend evidence READY in 148.8 seconds (9,116 input characters, 245 output tokens); three stored news events READY in 42.5 seconds (2,831 input characters, 176 output tokens). No quality flags. These are structurally admitted analyses, not certification of every semantic claim. Stored news replay allows up to 180 days and does not establish current freshness.
- Dividend fallback Ubuntu run 37169418767 passed: ITUB4 19 events and BBDC4 12 monthly events, both READ_OK, with no interactive provider dividend calls. Senior BUY and Opportunities comparisons also passed.
- Production catch-up run 37169940668 passed: ten actual pending items processed in two batches, ten READY, zero degraded/failed/deferred, zero remaining, no competing worker; 1,095.9 seconds total (about 18.3 minutes). This demonstrates actual batch closure, not guaranteed sustained capacity for arbitrary future arrivals.

## Block 3 and block 4

Economic calculations, sizing, cash conservation, source/horizon qualification, canonical senior inputs and interactive stored dividend reads remain deterministic. Broad LLM throughput and source coverage are not promised beyond the measurements above.

The Ubuntu HTTP process requires an authenticated service restart to load the new stored primary dividend reader. Automatic `sudo -n systemctl restart b3-runtime.service` is blocked by interactive authentication. Candidate checks and checkout updates do not establish that the active HTTP process has loaded the new reader.

New React frontend implementation and visual acceptance remain separate work after backend activation.

## Final end-of-day checkpoint — local 2026-10-03

Final Ubuntu run 37169879967 completed successfully, including deterministic workspace and focused senior economic acceptance. Runtime restart was explicitly BLOCKED by authenticated sudo. Candidate acceptance is distinct from the active HTTP process.

Remaining backend closure: correct issuer declaration-day calculation from UTC to America/Sao_Paulo, add a midnight-boundary regression, run relevant tests/CI and install the tested revision; then authenticated `sudo systemctl restart b3-runtime.service` and focused active HTTP acceptance of BBDC4 stored primary dividends, BUY comparison and Opportunities. Do not mark the backend activated before this check.

The four requested functional blocks are substantially implemented; block 4 activation is incomplete. New React visual validation remains later. Current BTG report coverage and complete complementary dividend coverage remain explicit limitations, not invented data. Advanced personal Outcome/Experience/Learning acceptance remains outside this scoped closure; its canonical ownership/configuration is not established.

## 2026-10-04 timezone correction and focused installation

Block 1 step 4 corrected declaration classification to `observed_at.astimezone(ZoneInfo('America/Sao_Paulo')).date()`. Eight midnight regressions cover both ON/PN classes at 00:00, 01:30, 02:59 and 03:00 UTC, retaining gross amounts, provenance and partial coverage. Local full suite: 924 passed.

Revision `a3dced7729f460187aaf44ba6a9809101bcc95d5`: CI run 37202675923 SUCCESS. Ubuntu focused run 37202673290 passed the CI gate and 21 relevant tests, then installed this exact revision at `/opt/b3-investment-options-agent` on 2026-10-04 12:37:19 UTC. `sudo -n systemctl restart b3-runtime.service` failed because interactive authentication is required. The user-reported earlier restart predates installation and does not activate the corrected revision.

Block 4 step 3 remains pending an authenticated restart after installation. Read-only post-restart acceptance verifies the installed correction ancestry, process start after provider installation, health, BBDC4 primary RI/12 monthly events/partial coverage, BUY ITUB4×BBDC4 and Opportunities. It does not replay Qwen or drain the production queue. Reports remain private on Ubuntu. No new frontend implementation has started.
