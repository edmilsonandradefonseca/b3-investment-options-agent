# ADR ? Quant Engine Benchmark: IBOV

## Status
Accepted

## Date
2026-09-13

## Decision
The official benchmark for relative market-risk metrics in the Quant Engine is the Ibovespa (IBOV).

## Scope
This benchmark is used for:
- Beta
- Correlation
- Future relative-performance metrics

## Architectural constraints
- The Quant Engine must not fetch IBOV data itself.
- Market and benchmark series are supplied to the engine as inputs.
- Series must be aligned by observation timestamp before calculations.
- Only information available at the calculation/snapshot time may be used.
- Missing or insufficient observations must result in `None`, not inferred values.
- Benchmark configuration must remain explicit and auditable.

## Rationale
IBOV is the project's reference representation of the Brazilian equity market and provides a consistent benchmark for measuring systematic market exposure and co-movement of B3 equities.

## Consequence
Beta and correlation become deterministic derived features of `QuantFeatures`, with IBOV as the default benchmark supplied by the upstream data layer.
