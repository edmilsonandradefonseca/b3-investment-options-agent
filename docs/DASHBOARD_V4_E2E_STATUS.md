# Dashboard V4 E2E — Functional Validation

**Status:** FUNCTIONAL BASELINE COMPLETE — provider/runtime calibration remains  
**Architecture baseline:** V4.0 frozen at merge commit `4c341227`  
**Validation branch:** `feature/v4-dashboard-e2e`

## Authoritative portfolio path

BTG Excel `Renda Variavel` → `BtgRendaVariavelLoader` → `PortfolioContext` → deterministic engines → Dashboard/Copilot context.

Only `Posição > Ações` and `Posição > Opções` are authoritative for positions. Auxiliary statement sections are ignored. BTG cash is **unknown**, not zero, because this snapshot does not provide the cash balance.

## UC-01…UC-12 reconciliation

| UC | Functional baseline | Remaining external/calibration work |
|---|---|---|
| 01 Portfolio Intelligence | IMPLEMENTED / TESTED | enrich sector/P&L when canonical inputs exist |
| 02 Options Lifecycle | IMPLEMENTED / TESTED | IV/Greeks require validated market provider |
| 03 Opportunity Discovery | IMPLEMENTED / TESTED | connect real market/valuation/options providers |
| 04 Strategy Comparison / What-if | IMPLEMENTED / TESTED | calibrate scenarios with real data |
| 05 Market & Regime | IMPLEMENTED / TESTED | feed live/historical canonical market features |
| 06 Factor Intelligence | IMPLEMENTED / TESTED | real factor construction, broader robustness/regime calibration |
| 07 Historical Reconstruction | IMPLEMENTED / TESTED | ingest real historical execution ledger |
| 08 Continuous Learning | IMPLEMENTED / TESTED | accumulate real finalized outcomes/cohorts |
| 09 Historical Similarity / RAG | IMPLEMENTED / TESTED | runtime Qdrant benchmark/calibration |
| 10 Research / News / Events | IMPLEMENTED / TESTED | connect research/news providers and entity-impact enrichment |
| 11 Risk / Scenario / Stress | IMPLEMENTED / TESTED | calibrate shocks and richer sensitivities |
| 12 Conversational Copilot | CONTEXT BOUNDARY IMPLEMENTED / TESTED | connect conversational LLM/UI to orchestrator |

## Safety and authority invariants

- deterministic/statistical services own measurable facts;
- LLMs may explain/synthesize but do not override deterministic facts;
- no opportunity is invented outside the canonical analytical pipeline;
- no autonomous order execution;
- point-in-time availability is mandatory;
- correlation/significance are not represented as causality;
- personal historical experience is not generalized into market probability;
- SQLite/Parquet own canonical structured truth; Qdrant/Neo4j are rebuildable projections;
- provenance and `as_of` remain visible through the pipeline.

## Real BTG validation — 2026-09-27

The user's current BTG statement was validated without committing private data. The two authoritative sections produced 21 stock rows + 26 option rows. Economic aliases such as `PETRPN→PETR4`, `GGBRPN→GGBR4`, `BRADPN→BBDC4`, and `CMIGPN→CMIG4` are resolved only for economic aggregation; broker source identifiers remain untouched.

## Next gate

The code baseline is ready to merge after branch CI/PR verification. The next phase is **provider/runtime integration and calibration**, followed by real end-to-end validation on Ubuntu/Qdrant/Neo4j/Streamlit where applicable.
