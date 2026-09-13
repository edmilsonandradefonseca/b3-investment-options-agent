# B3 Investment & Options Agent — Data Contract

**Version:** 1.0  
**Status:** Draft for implementation  
**Scope:** Phase 2.1 — Data Contract

---

## 1. Purpose

The Data Contract defines the internal data interface between external data providers and the B3 Investment & Options Agent.

Providers are replaceable. Internal data contracts are stable.

The analytical engines must not depend directly on a specific external provider.

Architecture:

    Provider
        ↓
    Provider Adapter
        ↓
    Data Contract
        ↓
    Point-in-Time Layer
        ↓
    Storage
        ↓
    Analytical Engines

---

## 2. Core Principles

1. External providers are replaceable.
2. Raw data must not be overwritten.
3. Normalized data is separated from derived data.
4. Every record must preserve provenance.
5. Point-in-time availability is mandatory for historical decisions.
6. Deterministic calculations belong to Python engines.
7. Data quality must be explicit.
8. Schemas are versioned.
9. Missing data must not silently become valid data.
10. Historical backtests must not use information unavailable at the decision timestamp.

---

## 3. Common Metadata

Data records should preserve:

- `instrument_id`
- `ticker`
- `observation_timestamp`
- `available_timestamp`
- `source`
- `source_record_id`
- `ingested_at`
- `schema_version`
- `quality_status`
- `quality_flags`

---

## 4. Observation vs Availability

These timestamps have different meanings.

### observation_timestamp

When the data refers to or was observed.

### available_timestamp

When the information became available to the investor/system.

They must never be treated as interchangeable.

Example:

A financial result may refer to:

    period_end = 2025-12-31

but become available only on:

    available_timestamp = 2026-02-20

A decision on 2026-01-15 cannot use that result.

---

## 5. Point-in-Time Rule

For a decision at:

    decision_timestamp

a record is usable only when:

    available_timestamp <= decision_timestamp

This rule is mandatory for historical backtesting and historical decision reconstruction.

---

## 6. Data Layers

### RAW

Original provider response.

RAW data must remain immutable.

### NORMALIZED

Provider-independent representation using the internal Data Contract.

### DERIVED

Calculated information produced by analytical engines.

Examples:

- moving averages
- volatility
- valuation ratios
- fair value
- margin of safety
- PUT score
- CALL score
- liquidity score
- risk score

---

## 7. Instrument Contract

`Instrument` identifies a tradable instrument.

Required:

- `instrument_id`
- `ticker`
- `name`
- `asset_type`
- `exchange`
- `currency`

Optional:

- `sector`
- `industry`
- `active_from`
- `active_to`

Ticker must not be treated as the permanent identity of an instrument.

---

## 8. Stock Market Data

`StockMarketData` represents market observations.

Fields include:

- `open`
- `high`
- `low`
- `close`
- `volume`
- `vwap`
- `currency`

Inherited metadata includes provenance and point-in-time information.

---

## 9. Fundamental Data

`StockFundamental` represents an individual financial metric.

Examples:

- revenue
- EBITDA
- EBIT
- net income
- net debt
- cash
- equity
- EPS
- ROE
- ROIC
- dividend

The contract stores:

- metric
- value
- period start
- period end
- report date
- unit
- availability timestamp
- source

Fundamental data must be modeled according to when it became available, not only according to the accounting period.

---

## 10. Corporate Actions

Supported categories include:

- DIVIDEND
- JCP
- STOCK_SPLIT
- REVERSE_SPLIT
- BONUS
- RIGHTS
- SUBSCRIPTION
- MERGER
- SPINOFF
- OTHER

Relevant dates include:

- announcement date
- ex-date
- record date
- payment date

---

## 11. Options

Options are represented by two contracts.

### OptionContract

Defines the identity and static characteristics of the option:

- `option_id`
- `underlying_id`
- `underlying_ticker`
- `option_ticker`
- `option_type`
- `strike`
- `expiration_date`
- `exercise_style`
- `contract_multiplier`
- `currency`

### OptionQuote

Defines the market state at a specific observation time:

- bid
- ask
- last
- mid
- volume
- open interest
- implied volatility
- delta
- gamma
- theta
- vega
- rho

The option contract and option quote must remain separate.

---

## 12. PUT and CALL Derived Data

PUT and CALL opportunities are not raw provider data.

They belong to the analytical layer.

Examples of derived PUT metrics:

- effective acquisition price
- premium yield
- annualized premium yield
- distance to spot
- distance to fair value
- margin of safety
- assignment risk
- liquidity score
- event risk

Examples of derived CALL metrics:

- premium yield
- annualized premium yield
- upside to strike
- potential total return
- opportunity cost
- exercise probability
- distance to fair value

---

## 13. Macro Data

`MacroObservation` represents an economic indicator.

Examples:

- SELIC
- IPCA
- CDI
- USD/BRL
- GDP
- unemployment
- IBOV

The contract preserves both observation and availability timing.

---

## 14. News and Events

News/event data will be introduced as a separate schema in a subsequent contract revision when the ingestion strategy is defined.

The current v1 contract intentionally does not define the complete news schema.

---

## 15. Data Quality

Allowed high-level states:

- `VALID`
- `WARNING`
- `INVALID`
- `MISSING`
- `STALE`
- `SUSPECT`

Quality flags may include:

- `MISSING_VOLUME`
- `DUPLICATE`
- `STALE_QUOTE`
- `INVALID_PRICE`
- `TIMESTAMP_MISSING`
- `SOURCE_CONFLICT`
- `CORPORATE_ACTION_PENDING`

Invalid or suspect records must not silently enter analytical calculations.

---

## 16. Provenance

The system must be able to answer:

> Where did this value come from?

At minimum:

- source
- source record ID when available
- ingestion timestamp
- schema version

---

## 17. Storage

Recommended storage architecture:

### Parquet

Historical and analytical datasets:

- prices
- fundamentals
- options
- macro
- normalized market data

### SQLite

Operational and decision data:

- runs
- decisions
- portfolio state
- LLM calls
- costs
- data quality events
- backtest metadata

---

## 18. Provider Independence

The analytical engines must consume internal schemas.

Correct:

    Provider
        ↓
    Adapter
        ↓
    Data Contract
        ↓
    Quant / Valuation / Options

Incorrect:

    Provider
        ↓
    Quant Engine

This allows providers to be replaced without redesigning analytical components.

---

## 19. Initial Python Schemas

The initial implementation is located under:

    src/b3_agent/schemas/

Current schemas:

- `common.py`
- `instrument.py`
- `market.py`
- `fundamental.py`
- `corporate_action.py`
- `option.py`
- `macro.py`

The schemas intentionally use standard-library dataclasses at this stage.

External validation libraries are deferred until their need is demonstrated.

---

## 20. Scope Boundaries

This version does NOT implement:

- B3 provider integration
- Yahoo Finance integration
- API credentials
- database persistence
- Parquet ingestion
- point-in-time filtering engine
- data quality engine
- news ingestion
- portfolio ingestion

Those belong to subsequent Phase 2 steps.

---

## 21. Versioning

Current contract:

    Data Contract v1.0

Any breaking change requires:

1. Change classification.
2. Architecture impact review.
3. Schema version decision.
4. Regression tests.
5. Documentation update.
6. Validation before freeze.

---

## 22. Acceptance Criteria

Data Contract v1 is accepted when:

- internal schemas exist;
- provider-specific concepts are not embedded in analytical schemas;
- provenance fields exist;
- observation and availability timestamps are separated;
- option contract and option quote are separated;
- raw, normalized and derived layers are defined;
- storage responsibilities are defined;
- point-in-time rule is explicit;
- tests validate the initial schemas.

---

## 23. Next Phase

Next implementation step:

**2.2 — Data Provider Strategy**

The provider strategy must be decided before implementing ingestion.

No provider-specific code should be added directly to the analytical engines.
