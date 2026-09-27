# Dashboard V4 E2E — Functional Validation

**Status:** IN PROGRESS  
**Architecture baseline:** V4 frozen at merge commit `4c341227`

## First functional slice

The dashboard is now treated as a read-only consumer of the frozen V4 domain.

Current E2E path:

BTG Excel → `BtgRendaVariavelLoader` → `PortfolioContext` → `PortfolioIntelligenceEngine` → dashboard

Options transactions remain a separate substitutive snapshot.

## Runtime alignment

The UI no longer presents Obsidian as a runtime knowledge component.

It exposes the frozen V4 ownership model:
- SQLite / Parquet — canonical structured state
- Qdrant — reconstructible RAG/retrieval projection
- Neo4j — reconstructible relationship projection

## Opportunity safety

Portfolio exposure alone is not treated as an opportunity signal. The Opportunities tab remains empty until validated upstream market/valuation/options analytical inputs are connected to the deterministic Opportunity pipeline.

## Next E2E slice

1. validate a real BTG XLSX against the current loader;
2. validate option transaction XLSX;
3. connect validated analytical inputs to `OpportunityPipeline.build_from_inputs`;
4. expose V4 regime/experience/learning/scenario outputs through `DashboardV4Presenter`;
5. run the 12 use cases against real/snapshot data.

## Implemented E2E seam

`DashboardE2EService` now provides a Streamlit-independent deterministic seam:

BTG XLSX → PortfolioContext → PortfolioIntelligence + optional Options Transactions → empty/sourced OpportunitySet

This is covered by a realistic generated XLSX fixture. It proves integration without requiring the user's private workbook in CI and preserves the rule that missing analytical inputs cannot be invented.


## Real BTG validation — 2026-09-27

Validated against the user's newer BTG statement using only the authoritative
`Renda Variavel` sections `Posição > Ações` and `Posição > Opções`.

Observed real-world integration requirement: some BTG option `Ativo Ref.`
identifiers use economic aliases such as `PETRPN`, `GGBRPN`, `BRADPN`
and `CMIGPN`, while cash equities use `PETR4`, `GGBR4`, `BBDC4` and
`CMIG4`.

The source identifier remains untouched in `Position.underlying_ticker`.
`InstrumentIdentityResolver` maps only the economic aggregation key used by
Portfolio Intelligence and Capital Risk. This prevents false uncovered-call
risk and split exposure buckets without corrupting broker provenance.

The alias table is intentionally explicit and deterministic. Unknown symbols
are preserved unchanged; no fuzzy or inferred ticker conversion is allowed.
