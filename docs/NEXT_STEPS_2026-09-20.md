# B3 Investment & Options Agent — Next Steps
## Checkpoint — 2026-09-20

## Current Status

### Phase 8 — UX / Visual

1. **UX-01 — Visual Audit** — DONE
2. **UX-02 — Common Visual Language** — PAUSED
   - UX-02a — Shared primitives — DONE
   - UX-02b — Apply common visual language across screens — IN PROGRESS / last E2E adjustments pending

**Stop point:** We are intentionally stopping at UX-02. Do not start UX-03 until UX-02b is completed and the Dashboard E2E gate is green.

### Remaining UX roadmap

3. **UX-03 — Responsive / adaptive layout**
4. **UX-04 — Loading / empty / error states**
5. **UX-05 — Tables / density / readability**
6. **UX-06 — Navigation / accessibility**
7. **UX-07 — Visual polish / final audit**

---

# Next Major Objective

After completing Phase 8 UX, build the **local B3 Runtime** that starts and connects the backend components so the application no longer depends on manually starting Python processes.

Target user experience:

```
B3 Investment Copilot.exe
        ↓
B3 Runtime
        ↓
Orchestrator :8000
        ↓
LangGraph
        ↓
Agents / Deterministic Engines / Knowledge
```

The Runtime is an infrastructure/startup layer. It must NOT become a second intelligence orchestrator.

---

# Runtime Architecture

## Runtime responsibilities

The Runtime should:

- initialize/check the local application environment;
- create/check persistent data directories;
- initialize SQLite when required;
- start the B3 Orchestrator;
- verify health/readiness;
- manage local service lifecycle;
- expose runtime/service status;
- prepare the application for the Tauri/React client.

The Runtime must NOT:

- implement investment logic;
- calculate portfolio metrics;
- sequence investment agents;
- perform LLM reasoning;
- replace LangGraph;
- bypass Risk Validation.

Architectural boundary:

```
Runtime
  ↓
B3 Orchestrator Server
  ↓
LangGraph
  ↓
Agents / Deterministic Engines / Knowledge
```

---

# Persistent Data Architecture

The frozen V3.1 architecture defines structured persistence as:

```
SQLite / Parquet
```

and explicitly includes:

- market data;
- portfolio data;
- calculations;
- rankings;
- audit;
- backtests;
- performance.

Therefore the next data-layer objective is:

```
BRAPI / OpLab / B3 APIs
          ↓
      Connectors
          ↓
 Canonical Market Data
          ↓
   Validation + Provenance
          ↓
     SQLite / Parquet
          ↓
 Market Data Repository
          ↓
      LangGraph
```

## SQLite

Use for structured/operational state such as:

- portfolio;
- transactions;
- option ledger;
- positions;
- manifests;
- audit;
- metadata.

## Parquet

Use for persistent historical datasets such as:

- historical prices / OHLCV;
- historical option data;
- historical market datasets;
- backtest datasets;
- other high-volume time-series data.

Do not introduce another database merely for historical market data without a validated use case.

---

# Market Data Layer

Implement a canonical market-data boundary before expanding infrastructure.

Target:

```
BRAPI Connector ─┐
                 ├→ Market Data Adapter
OpLab Connector ─┘
                         ↓
                Canonical Market Model
                         ↓
                  Persistence Layer
                   ┌─────┴─────┐
                   ↓           ↓
                SQLite      Parquet
```

Requirements:

- source/provider;
- instrument identity;
- `as_of`;
- `retrieved_at`;
- provenance;
- schema/version;
- source manifest/checksum where applicable;
- historical/PIT semantics;
- idempotent ingestion.

The connector must not become the persistence layer.

---

# Qdrant / RAG / Knowledge Graph

Do NOT install or make Qdrant/Neo4j mandatory as the next step merely because the Runtime exists.

The current architecture keeps:

- Obsidian = persistent human-readable knowledge;
- RAG = semantic retrieval over selected knowledge;
- Knowledge Graph = explicit relationships;
- Knowledge Graph implementation = later extension.

When implemented:

```
Obsidian
   ↓
Knowledge Ingestion
   ↓
Chunk / Metadata / Embedding
   ↓
Vector Store
```

and:

```
Entities / Relationships
          ↓
   Knowledge Graph
```

The Runtime should be designed so these services can be added later without changing the Orchestrator API or LangGraph contracts.

---

# Implementation Sequence

## Phase 8 — Finish UX first

- [ ] UX-02b — finish common visual language E2E
- [ ] UX-02 freeze
- [ ] UX-03 — responsive/adaptive layout
- [ ] UX-04 — loading/empty/error states
- [ ] UX-05 — tables/density/readability
- [ ] UX-06 — navigation/accessibility
- [ ] UX-07 — visual polish/final audit
- [ ] Dashboard final E2E
- [ ] CI green
- [ ] Freeze Phase 8

## Runtime Foundation

- [ ] Define Runtime Manager contract
- [ ] Define `/runtime/status`
- [ ] Define startup/shutdown lifecycle
- [ ] Start/check Orchestrator
- [ ] Initialize/check SQLite
- [ ] Define data directories
- [ ] Add health/readiness checks
- [ ] Connect Tauri startup to Runtime
- [ ] Validate Windows executable
- [ ] Remove need for manual `uvicorn` / Python startup

## Market Data Persistence

- [ ] Define canonical Market Data model
- [ ] Define Market Data Repository interface
- [ ] Define BRAPI adapter
- [ ] Define OpLab adapter
- [ ] Persist historical data
- [ ] Add provenance/PIT metadata
- [ ] Add idempotent ingestion
- [ ] Add market-data integration tests
- [ ] Validate real historical query from Dashboard

## Later

- [ ] RAG/vector store implementation when justified by use cases
- [ ] Knowledge Graph implementation when justified
- [ ] Runtime management of optional knowledge services
- [ ] Backtest / walk-forward persistence validation

---

# Validation Gate

Do not advance a phase until:

```
IMPLEMENT
   ↓
TEST
   ↓
CI
   ↓
DASHBOARD VALIDATION
   ↓
DOCUMENT
   ↓
FREEZE
   ↓
NEXT PHASE
```

---

# Important Architectural Invariants

- Dashboard is the human-facing application.
- B3 Orchestrator Server is the API/service boundary.
- LangGraph is the workflow brain.
- Deterministic engines remain authoritative for numerical calculations.
- MCP/services provide controlled access to external/internal resources.
- SQLite/Parquet provide structured persistent storage.
- Obsidian provides persistent human-readable knowledge.
- RAG provides contextual evidence.
- Knowledge Graph represents explicit relationships.
- LLM is for reasoning/synthesis, not deterministic calculation.
- Risk Validation remains downstream and deterministic.
- No autonomous trading.
- Historical analysis must preserve provenance and PIT semantics.
- Clients must not access internal resources directly.
- The Runtime must not become a second orchestration/intelligence layer.

# Tomorrow — First Action

Resume at:

**UX-02b → finish last Dashboard E2E adjustment → run CI → freeze UX-02.**

Only after Phase 8 is complete:

**start Runtime Foundation design/implementation.**

