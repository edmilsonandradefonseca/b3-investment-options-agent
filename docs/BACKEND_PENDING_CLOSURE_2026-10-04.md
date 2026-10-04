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
- Dedicated broader validation now also reads temporally admissible stored news when none is pending, and requires both bundle classes. Historical replay is separate from current freshness.
- A bounded production catch-up job verifies actual backlog drain, rather than extrapolating two-report timings.

## Block 3 and block 4

Economic calculations, sizing, cash conservation, source/horizon qualification, canonical senior inputs and interactive stored dividend reads remain deterministic. Broad LLM throughput and source coverage are not promised beyond the measurements above.

The Ubuntu HTTP process requires an authenticated service restart to load the new stored primary dividend reader. Automatic `sudo -n systemctl restart b3-runtime.service` is blocked by interactive authentication. Candidate checks and checkout updates do not establish that the active HTTP process has loaded the new reader.

New React frontend implementation and visual acceptance remain separate work after backend activation.
