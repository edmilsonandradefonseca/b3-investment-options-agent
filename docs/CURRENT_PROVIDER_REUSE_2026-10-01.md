# Current OPLAB acquisition reuse

Additive performance block on the existing stock/option adapters. No schema migrations, durable cache, LLM router, execution or DeepSeek dependency.

- Current stock quotes and the complete current PUT/CALL chain are reused for at most five seconds in the same process. Bounded singleflight prevents duplicate concurrent acquisition. Keys separate endpoint, asset, credential and transport. Financial calculations and portfolio eligibility continue to run over the current portfolio; these provider caches contain no portfolio/ranking decision.
- Successful normalized stock records and schema-validated raw chains only. Exceptions and malformed/non-finite results are not admitted. Callers get isolated copies. Tokens are never exposed in telemetry.
- Observation, availability and ingestion timestamps are preserved on reuse; a HIT does not relabel evidence as newly collected. When an option has no provider time, the fallback is the actual acquisition timestamp, with `provider_timestamp_missing`, rather than the caller's arbitrary `as_of`. Current endpoints are not historical replay sources.
- Current quote/option endpoints expose `reuse_telemetry` with HIT/MISS/COALESCED, latency and TTL. LiveProviderSnapshot carries acquisition telemetry; deterministic asset packs carry quote reuse telemetry.
- This is a short bounded freshness window, not a claim that a five-second-old quote is executable now. Returned timestamps remain the freshness evidence. Authority and human confirmation remain unchanged.

Existing BRAPI caches and local-history precedence remain unchanged. Whole-workspace research/context reuse, historical reconstruction, similarity and full agent-latency comparison remain open. This block reduces repeated OPLAB acquisition across the current existing workspace/service paths; it does not guarantee cached senior output or a measured decrease in the previous 80–95 seconds.

Validation: full Python suite passed locally, including cache expiry/credential separation, original timestamps, PUT/CALL shared response and rejection of malformed chains. `scripts/validate_current_reuse_real.py` measures two consecutive stock reads and two chain reads without invoking models. Run only after CI-green deployment/restart. Its live check requires configured OPLAB and successful current data.
