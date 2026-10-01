# B3 Agent — Status / Handoff 2026-09-27

## Baseline
- Architecture V4.0: APPROVED / FROZEN.
- Functional UC-01 through UC-12 baseline: implemented, reconciled and tested.
- PR #25 merged to main at `47aa41bc6209e89ac119e32ea5e81081b9b708ff`.
- Post-merge CI run 862: SUCCESS.
- Functional freeze PR #26 merged to main at `6e89ab7facbb19103b3e763e830ebd1eac002ca9`.
- Post-freeze CI run 864: SUCCESS.

## Functional scope completed
- BTG Renda Variavel authoritative ingestion: only Posição > Ações and Posição > Opções.
- Real BTG validation: 21 stock rows + 26 option rows = 47 positions; private workbook not committed.
- Economic identity aliases for aggregation without mutating broker identifiers.
- UC-01 Portfolio Intelligence.
- UC-02 Options Intelligence / expiration risk.
- UC-03 Opportunity pipeline with explicit upstream inputs and provenance.
- UC-04 Strategy Comparison / What-if.
- UC-05 Market Regime.
- UC-06 Factor Intelligence: BH multiple-testing correction, time holdout, direction stability, walk-forward robustness; association only, no causal claim.
- UC-07 Historical Operation Reconstruction + deterministic outcomes.
- UC-08 Continuous Learning over compatible personal-experience cohorts with selection-bias warning.
- UC-09 Historical Similarity / RAG with structured ranking, optional semantic candidates and trace.
- UC-10 PIT-safe Research/News/Event normalization.
- UC-11 Risk/Stress, including correct UNKNOWN cash semantics for BTG snapshots.
- UC-12 deterministic Copilot context boundary; explain/compare/summarize only; no trade/order execution.
- Dashboard surfaces updated for opportunities, decision context and factor intelligence.

## Runtime integration work started
Branch: `feature/v4-runtime-integration`
PR: #27
Head when handoff was prepared: `1ad64e48dcd05f643456b85895f86a3203040f32`

Added:
- `docs/V4_RUNTIME_INTEGRATION.md`
- `scripts/runtime_preflight.sh`

Runtime direction:
- `infra/docker-compose.yml` is the canonical integrated local stack.
- Qdrant pinned at v1.19.1.
- Neo4j pinned at 2026.08.1.
- Qdrant production vector contract: 768d + hybrid dense/sparse.
- SQLite/Parquet remain canonical structured truth.
- Qdrant/Neo4j remain rebuildable projections.

## Current real-world gate
The Ubuntu machine does NOT have the repository at `~/b3-investment-options-agent`.

Attempted:
```bash
cd ~/b3-investment-options-agent
```
Result:
```
-bash: cd: /home/edmilson/b3-investment-options-agent: No such file or directory
```

No repository changes were made on Ubuntu by that failed command sequence.

Next action is to locate an existing clone under home or /opt. If none exists, clone the B3 repository before running the runtime preflight.
