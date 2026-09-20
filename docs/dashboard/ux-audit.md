# Dashboard UX-01 — Visual Audit

## Baseline

- Branch: `feature/mcp-mvp`
- Baseline commit: `c766bdbfa106e66123ee5aea816edb00c140b7c2`
- Phase 7: FROZEN
- Phase 8: IN PROGRESS
- Scope: presentation only

## Current visual system observed

The Dashboard already has a coherent dark financial-console direction:
- dark blue/navy shell;
- blue primary interaction;
- green positive/online states;
- red negative/error states;
- compact typography;
- card/panel based layout;
- left navigation;
- optional right Copilot rail;
- responsive breakpoint behavior.

This is a strong starting point. Phase 8 should consolidate it rather than replace it with a different visual paradigm.

## UX-01 findings

### P0 — Structural

1. **Global viewport constraint**
   - `body` currently uses `min-width:1200px`.
   - This prevents a genuinely narrow/mobile viewport from adapting naturally.
   - The CSS has responsive breakpoints, but the body minimum width limits their effect.
   - Action: replace the hard minimum with an adaptive strategy after verifying critical desktop/table behavior.

2. **Three-column shell changes abruptly**
   - The right Copilot rail disappears at <=1250px.
   - The navigation/content proportions also change at the same breakpoint.
   - Action: define explicit desktop, compact-desktop and narrow layouts.

3. **Repeated page primitives**
   - Existing pages independently compose headers, panels, metrics, tables, warnings and empty states.
   - Action: introduce presentation primitives/classes without moving business logic.

### P1 — Consistency

4. **Page header hierarchy**
   - `.workspace-head` is established, but individual views do not consistently expose the same title/subtitle/status structure.
   - Action: standardize page header.

5. **Quality/status presentation**
   - Quality is currently rendered through different visual patterns depending on the view.
   - Action: one reusable quality/status badge treatment for VALIDATED/WARNING/REJECTED/STAGED.

6. **Provenance and `as_of`**
   - Source and date-base information exists but is not consistently grouped.
   - Action: standard provenance block.

7. **Warnings**
   - Reconciliation already has `.warning-text`, but warning/review states need a common visual container.
   - Action: reusable warning/review callout.

8. **Empty/loading/error states**
   - Existing views have state-specific messages, but presentation is not standardized.
   - Action: common state component/class for loading, empty and error.

### P1 — Information density

9. **Tables**
   - Tables use a compact 9px font.
   - Several views can contain many columns.
   - Action: improve table readability and overflow behavior without hiding material columns.

10. **Opportunity cards**
   - Opportunity cards are visually distinct but should share the same metric/meta conventions as other cards.
   - Action: consolidate card spacing, metadata labels and status treatment.

11. **Knowledge**
   - Evidence, entities and provenance should use the same panel/table vocabulary as Reconciliation and Opportunities.

12. **Copilot**
   - Copilot has its own visual language and denser layout.
   - Action: preserve its conversational character while aligning global typography, status and provenance primitives.

### P2 — Navigation

13. **Navigation labels**
   - Current navigation mixes English product concepts and Portuguese subtitles.
   - This is acceptable for the current product identity, but hierarchy can be clearer.
   - Action: retain existing names unless product terminology changes; improve active/section hierarchy rather than rename functionality.

14. **Data & Connections**
   - Upload actions and connection indicators are currently grouped together.
   - Action: distinguish connection state from ingestion actions visually.

15. **Knowledge status**
   - Obsidian/RAG/Knowledge Graph are presented as backend indicators.
   - Action: keep these informational and clearly separate from user actions.

## P2 — Accessibility / interaction

16. **Color-only semantics**
   - Positive/negative/status information sometimes relies on color.
   - Action: retain text/icon labels so meaning does not depend only on color.

17. **Keyboard/focus**
   - Existing button styling emphasizes hover/active but a common visible focus treatment should be added.
   - Action: define global `:focus-visible` treatment.

18. **Interactive controls**
   - Upload labels, navigation buttons and cards should have consistent hover/focus/disabled states.

## Proposed Phase 8 design primitives

Create presentation-only primitives/classes for:

- `PageHeader`
- `MetricCard`
- `QualityBadge`
- `ProvenanceBlock`
- `WarningCallout`
- `StatePanel`
- `DataTable`
- `SectionPanel`
- `MetaGrid`

These must not calculate investment semantics.

## Proposed responsive model

### Desktop
- full left navigation;
- main workspace;
- Copilot rail where available.

### Compact desktop
- left navigation;
- main workspace;
- Copilot collapses or becomes a page-level panel.

### Narrow
- navigation becomes compact/collapsible;
- single-column workspace;
- tables use horizontal scrolling rather than losing columns;
- Copilot becomes a dedicated view/panel.

## UX-01 conclusion

The existing Dashboard does not need a visual rewrite. It needs **consolidation**.

The highest-value sequence is:

1. remove the hard viewport constraint;
2. establish shared page/header/status primitives;
3. standardize quality/provenance/warnings;
4. standardize state and table behavior;
5. add focus/interaction states;
6. validate all seven views with Playwright;
7. then perform the final visual polish.

## Next implementation step

**UX-02 — Common visual language.**

Do not change Orchestrator contracts or analytical logic during UX-02.
