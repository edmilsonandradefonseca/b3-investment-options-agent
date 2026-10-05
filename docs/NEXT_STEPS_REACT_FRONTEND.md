# Next Steps — React Frontend Phase

## Objective

Start the production React frontend for the B3 Investment & Options Agent without reopening the frozen backend architecture.

## Starting point

Backend runtime is validated and should be treated as the source of truth.

Primary frontend goal:

```text
React UI
  -> B3 backend APIs
  -> deterministic/statistical services
  -> runtime providers / canonical stores
```

Do not duplicate investment logic in React.

## Phase 1 — Frontend foundation

1. Inspect the existing frontend code and build configuration.
2. Define the React application shell and routing.
3. Create the API client layer for the B3 backend.
4. Define TypeScript contracts aligned with backend response schemas.
5. Add environment configuration for backend base URL.
6. Establish loading, error and empty states.

## Phase 2 — Core screens

Implement in this order:

1. Portfolio
   - current positions
   - exposures
   - concentration
   - option obligations
   - capital risk

2. Options Intelligence
   - option positions
   - live chain
   - PUT/CALL opportunities
   - expiration and assignment risk

3. Opportunities
   - ranked opportunities
   - filters
   - deterministic score components
   - evidence/source references

4. Market Intelligence
   - current market regime
   - macro snapshot
   - research/news evidence
   - freshness / as-of indicators

5. Risk & Scenarios
   - stress scenarios
   - position impact
   - portfolio impact
   - assumptions

6. Historical / Learning
   - operations
   - outcomes
   - historical similarity
   - learning status
   - gracefully handle insufficient-history states

7. Copilot
   - explanation/synthesis only
   - show evidence and freshness
   - never expose autonomous trade execution controls

## Phase 3 — UX and operating requirements

- Preserve as-of timestamps everywhere.
- Show data quality and limitations explicitly.
- Distinguish deterministic facts from generated explanation.
- Surface evidence IDs/source refs where relevant.
- Never hide UNKNOWN cash semantics.
- Never infer missing values in the frontend.
- Keep all trading actions informational; no order execution.
- Use responsive layout suitable for desktop first.
- Avoid spending time improving legacy Streamlit UI except as a regression/smoke harness.

## Phase 4 — Integration acceptance

Before declaring the frontend complete:

- validate all major screens against the real 47-position BTG portfolio;
- validate multi-ticker provider behavior;
- validate options with current OPLAB chain;
- validate macro freshness;
- validate Qdrant/Neo4j-backed evidence surfaces;
- validate UC01-UC12 presentation;
- ensure UC-06/08/09 show LIMITED/insufficient-history states correctly;
- run production build and backend/frontend smoke tests.

## First action in the next chat

Read these files first:

- `docs/BACKEND_RUNTIME_VERIFIED_FREEZE_2026-09-27.md`
- `docs/NEXT_STEPS_REACT_FRONTEND.md`
- `docs/V4_FUNCTIONAL_VERIFIED_FREEZE_2026-09-27.md`
- `docs/USE_CASE_ARCHITECTURE_TRACEABILITY_V2.0.md`

Then inspect the current frontend tree and backend API routes before changing code.

The first coding task should be to establish the React shell + typed API client against existing backend endpoints.
