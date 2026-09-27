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
