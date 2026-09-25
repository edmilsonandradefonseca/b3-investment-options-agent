# Dashboard UX / Visual — Phase 8

## Status

**IN PROGRESS — UX-02b implementation**

Phase 7 Knowledge UI is frozen. Phase 8 starts from the last green Dashboard gate.

Baseline:
- Commit: `c761d7aa4c2de181ae5b8a2a5e1e3ebfefa7fd45`
- CI #682: SUCCESS
- Dashboard + Copilot Gate #167: SUCCESS

## Objective

Turn the already functional React Dashboard into a coherent operational interface while preserving the existing analytical contracts.

The UX layer must make it easier to answer:
- Onde estou?
- Qual é a qualidade dos dados?
- De quando são os dados?
- Qual é a fonte?
- O que precisa da minha atenção?
- O que posso investigar a seguir?

## Non-negotiable architecture rules

1. React remains presentation-only.
2. Business rules remain in Python.
3. The Orchestrator remains the analytical boundary.
4. No ranking, valuation, capital, risk or reconciliation logic is recreated in TypeScript.
5. Existing API contracts are preserved unless a concrete requirement proves otherwise.
6. No autonomous trading/execution.
7. Qdrant/Neo4j are not introduced as a UX dependency.
8. Every material state must remain visible; UX may improve hierarchy but must not hide warnings or uncertainty.

## Current views to harmonize

- Portfolio
- Options Intelligence
- Portfolio Intelligence
- Reconciliation
- Opportunities
- Knowledge
- Copilot

## Phase 8 work packages

### UX-01 — Visual audit

Inventory existing:
- typography;
- spacing;
- navigation;
- page headers;
- metric cards;
- tables;
- badges;
- warnings;
- empty/loading/error states;
- responsive behavior.

Deliverable: short audit and concrete inconsistencies to fix.

### UX-02 — Common visual language

Define reusable presentation primitives:
- page shell/header;
- section header;
- metric card;
- quality/status badge;
- provenance/as-of block;
- warning/review callout;
- empty state;
- data table;
- opportunity/card pattern.

No business semantics are introduced by these primitives.

### UX-02b — Apply common language to current views

Implemented presentation-only consolidation across the current React views:
- shared `PageHeader` for page title/subtitle/status;
- shared `QualityBadge`, `ProvenanceBlock`, `WarningCallout` and `StatePanel` primitives;
- common keyboard focus treatment;
- adaptive viewport behavior replacing the hard `1200px` body minimum;
- shared provenance treatment applied to opportunity/reconciliation surfaces.

No Orchestrator contract or analytical business rule was changed.

### UX-03 — Navigation and orientation

Make the current navigation predictable and visually consistent. Every page should expose:
- page title;
- concise purpose/subtitle;
- current data status where applicable;
- obvious primary content;
- clear route back to adjacent analytical views.

### UX-04 — Data quality and provenance

Standardize visual treatment for:
- VALIDATED;
- WARNING;
- REJECTED;
- STAGED;
- `as_of`;
- source references;
- review-required conditions.

The UI must not turn a warning into a positive signal through visual ambiguity.

### UX-05 — Information density

Improve readability for:
- tables with many columns;
- opportunity cards;
- reconciliation matches;
- Knowledge evidence/entities;
- Copilot results.

Prefer hierarchy, grouping and progressive disclosure over removing material information.

### UX-06 — Responsive behavior

Validate desktop first, then narrower viewport behavior. No material data should become inaccessible because of viewport width.

### UX-07 — Regression coverage

Add Playwright assertions for the stable visual/interaction contracts introduced by Phase 8. Avoid brittle pixel-level tests.

## Acceptance criteria

Phase 8 can be frozen only when:

- all current views use the common visual language;
- navigation is consistent;
- quality/provenance/as-of states are visually standardized;
- loading, empty and error states are explicit;
- warnings remain visible and distinguishable;
- responsive behavior has automated coverage for the agreed critical interactions;
- existing backend and Dashboard E2E suites remain green;
- no analytical business logic has moved to React;
- CI is green;
- manual Dashboard validation confirms the intended user flow;
- documentation reflects the final implementation.

## Explicit non-goals

- No new investment strategy.
- No new valuation model.
- No new risk engine.
- No new opportunity ranking algorithm.
- No database migration.
- No Qdrant/Neo4j installation.
- No Tauri packaging.

## Definition of Done

**Audit → Design system → Implement → E2E/regression → CI → Dashboard validation → Document → Freeze**

After freeze, Phase 9 is Tauri/.exe packaging.
