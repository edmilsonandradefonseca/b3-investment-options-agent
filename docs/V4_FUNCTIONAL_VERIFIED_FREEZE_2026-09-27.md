# V4 Functional Baseline — Verified Freeze

**Date:** 2026-09-27
**Status:** VERIFIED / FROZEN FUNCTIONAL BASELINE
**Architecture:** V4.0 APPROVED / FROZEN
**Functional merge:** PR #25
**Merge commit:** `47aa41bc6209e89ac119e32ea5e81081b9b708ff`
**Post-merge CI:** run 862 — SUCCESS

## Scope
The deterministic/statistical functional baseline for UC-01 through UC-12 is implemented, reconciled and regression-tested on `main`.

Included: authoritative BTG Ações/Opções ingestion; economic instrument identity; portfolio/options intelligence; unknown-cash semantics; deterministic opportunity pipeline; strategy comparison; scenario/stress; market regime; factor intelligence with multiple-testing correction, holdout stability and walk-forward robustness; historical operation reconstruction/outcomes; compatible-cohort continuous learning; historical similarity retrieval/trace; PIT-safe research events; deterministic Copilot context; V4 dashboard surfaces.

## Safety and authority invariants
1. Deterministic/statistical services own measurable facts.
2. LLMs may synthesize/explain but do not override canonical facts.
3. No opportunity is invented outside the canonical analytical pipeline.
4. No autonomous trade/order execution is in scope.
5. Historical analysis respects point-in-time availability.
6. Statistical association is not represented as causality.
7. Personal experience is not generalized into market probability.
8. SQLite/Parquet own canonical structured truth; Qdrant and Neo4j are rebuildable projections.
9. Provenance, quality and `as_of` remain explicit.
10. Human remains final investment decision authority.

## Real-data validation
The private BTG workbook was not committed. Its authoritative `Renda Variavel` sections produced 21 stock rows and 26 option rows (47 positions), validating the real-world parsing contract while keeping private data outside Git.

## Next phase — V4 Runtime Integration & Calibration
1. Synchronize Ubuntu checkout to this verified `main` baseline.
2. Run full local regression and Streamlit smoke test.
3. Validate Qdrant/Neo4j runtime and projections.
4. Connect canonical market/options/research providers.
5. Ingest/replay historical transaction data.
6. Run UC-01 through UC-12 real-data acceptance scenarios.
7. Calibrate retrieval, factors, regimes and stress.
8. Record a runtime-verified release candidate.

Architecture V4.0 remains frozen. Provider adapters, calibration and runtime fixes do not automatically reopen architecture.