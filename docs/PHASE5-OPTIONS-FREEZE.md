# Phase 5 — Options Freeze

Status: FROZEN
Date: 2026-09-14

## Scope

Phase 5 implements the deterministic options analysis foundation for cash-secured PUT and covered CALL opportunities.

## Implemented

- PUT analysis engine: effective acquisition price, premium return, annualized return, fair value and margin of safety.
- Covered CALL analysis engine: premium return, annualized premium return, gain to strike, total return if assigned, fair value and upside surrendered.
- Configurable contract multiplier; no hard-coded B3 multiplier in analysis logic.
- Unified options analysis contract combining PUT and CALL opportunities.
- Explicit deterministic options policy with configurable thresholds.
- Policy actions: SELL_PUT, SELL_CALL, HOLD_WAIT and AVOID where the available evidence is insufficient.
- Deterministic validation and automated tests.

## Data limitations intentionally deferred

The current provider layer may not supply OI, IV, Greeks or complete liquidity fields. These remain optional evidence and are not fabricated or made mandatory by the Phase 5 engine.

Capital allocation, portfolio concentration, covered-call coverage validation, open-position lifecycle and assignment capital belong to Phase 6 Portfolio Intelligence.

Transaction costs, taxes, corporate events and richer liquidity policy require their respective data contracts and are not silently approximated here.

## Deterministic convention

Initial annualized premium return uses simple annualization:

`premium_return * 365 / days_to_expiration`

This is an analytical convention, not a forecast. Any future change must be explicit, versioned and covered by regression/golden tests.

## Validation

Phase 5 tests cover PUT, CALL, unified options analysis and policy behavior. The GitHub Actions CI is required to remain green before progressing to Phase 6.

## Freeze boundary

No Portfolio implementation is included in this freeze. Phase 6 starts with the authoritative portfolio ingestion and Position/Position Intelligence contracts already defined by the project architecture.
