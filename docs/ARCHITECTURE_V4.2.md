# B3 Investment & Options Agent — Architecture V4.2

**Version:** 4.2  
**Status:** APPROVED ARCHITECTURAL BASELINE — implementation pending  
**Date:** 2026-09-29  
**Supersedes:** V4.1 only where explicitly stated in this document  
**Preserves:** all V4.0/V4.1 deterministic, routing, storage, PIT, human-authority and no-autonomous-trading invariants unless explicitly amended below

---

## 1. Executive summary

V4.2 adds a **Zero-Cost Resilient Evidence & Market Intelligence layer** to the B3 Investment & Options Agent.

The purpose is not to redesign the financial core, routing layer, RAG/KG stack, or reasoning hierarchy. V4.2 addresses one concrete weakness revealed during V4.1 acceptance:

> a search provider failure or restrictive search query can incorrectly appear as “no material event”.

The V4.2 architectural response is to separate:

1. **evidence acquisition**;
2. **evidence normalization and PIT validation**;
3. **event construction and deterministic materiality**;
4. **LLM reasoning**.

The central architectural rule is:

> **SearXNG is a discovery mechanism, not the source of truth. Official disclosures and public authoritative sources are first-class providers.**

The new evidence plane must operate at **R$ 0 external API cost for news, corporate events and market-intelligence evidence acquisition**.

---

## 2. Architectural lineage

V4.2 is additive:

```text
V4.0
Deterministic / Statistical Financial Truth
              +
V4.1
Fast Routing + Local/Senior Reasoning
              +
V4.2
Zero-Cost Evidence Acquisition & Reliability
```

V4.2 does **not** reopen V4.0 or V4.1 architecture decisions that are unrelated to evidence acquisition.

---

## 3. Preserved V4.0 / V4.1 invariants

The following remain unchanged:

- deterministic/statistical services remain authoritative for numerical facts;
- portfolio/accounting truth remains structured and deterministic;
- SQLite/Parquet remain canonical stores for structured truth;
- Qdrant remains a semantic projection;
- Neo4j remains a relationship/context projection;
- point-in-time correctness is mandatory;
- Fast Router remains deterministic/code-first;
- DeepSeek remains local/background reasoning;
- OpenClaw/Luna remains senior reasoning/escalation;
- LLMs do not create authoritative prices, P&L, rankings or market facts;
- opportunity generation remains owned by the opportunity pipeline;
- no autonomous order execution;
- human remains final investment authority;
- provider details remain behind adapters/contracts;
- RAW / NORMALIZED / DERIVED separation remains mandatory;
- provider failures must fail visibly, never silently fabricate completeness.

---

## 4. New non-negotiable invariant — ZERO-PAID-INTELLIGENCE

### 4.1 Rule

For **news, corporate events and market-intelligence evidence acquisition**:

> **No critical production path may depend on a paid commercial API.**

External API/provider cost for those domains must be:

> **R$ 0**

Permitted acquisition mechanisms include:

- official free services;
- free APIs;
- public structured downloads;
- public data files;
- RSS/Atom;
- public investor-relations pages;
- public regulator/agency pages;
- self-hosted SearXNG;
- controlled public-page fetching/scraping when technically and legally appropriate.

### 4.2 Scope boundary

This invariant applies to **evidence acquisition for UC-05 / UC-10 and related news/event intelligence**.

It does not automatically prohibit existing providers for other deterministic domains such as options-chain data or other already-separated structured market-data domains. Those remain governed by their own provider strategy and contracts.

### 4.3 Failure behavior

If a material intelligence fact is unavailable through allowed zero-cost sources:

```text
UNAVAILABLE / COVERAGE_GAP
```

is the correct outcome.

The system must not silently fall back to a paid news/event API.

---

## 5. Problem discovered during V4.1 acceptance

The V4.1 20-stock pilot validated:

- routing;
- structured market-provider access;
- batch execution;
- resource usage;
- no-material-event skip behavior.

However, it did **not** validate UC-10 evidence acquisition.

For WEGE3 the persisted result showed:

```text
raw_result_count       = 0
dated_recent_count     = 0
raw_event_count        = 0
material_event_count   = 0
```

while direct diagnostic queries to the same local SearXNG returned many results when the restrictive `news + time_range=day` combination was relaxed.

Therefore:

```text
SEARCH FAILURE / INSUFFICIENT COVERAGE
            !=
NO MATERIAL EVENT
```

V4.2 makes that distinction a first-class contract.

---

## 6. V4.2 high-level architecture

```text
                   REACT / API / SCHEDULER / COPILOT
                                  |
                                  v
                         FAST ROUTER V1
                           [V4.1 unchanged]
                                  |
                                  v
                         UC-05 / UC-10
                                  |
                                  v
                 EVIDENCE ACQUISITION PLANE V4.2
                                  |
              +-------------------+-------------------+
              |                                       |
              v                                       v
       OFFICIAL EVIDENCE                       OPEN-WEB EVIDENCE
              |                                       |
     +--------+---------+                    +--------+----------+
     |        |         |                    |        |          |
     v        v         v                    v        v          v
 CVM RAD   CVM OPEN    B3                RSS/RI   SEARXNG   PUBLIC WEB
 PRIMARY    DATA     BEST-EFFORT
 CURRENT  BACKFILL
     |        |         |                    |        |          |
     +--------+---------+-------------+------+--------+----------+
                                      |
                                      v
                         PROVIDER RESULT ENVELOPE
                     status / cursor / coverage / errors
                                      |
                                      v
                            IMMUTABLE RAW LANDING
                                      |
                                      v
                         EVIDENCE NORMALIZATION
                       existing Evidence contract
                                      |
                                      v
                               ENTITY MAPPING
                           issuer <-> securities
                                      |
                                      v
                           PIT / VALIDATION GATE
                                      |
                                      v
                             DEDUPLICATION
                                      |
                                      v
                              EVENT CLUSTER
                         Evidence[] -> Event
                                      |
                                      v
                         MATERIALITY ENGINE
                      deterministic + versioned
                              |               |
                         NON_MATERIAL    MATERIAL/CANDIDATE
                              |               |
                              |               v
                              |      ORIGINAL DOCUMENT FETCH
                              |               |
                              +-------+-------+
                                      |
                                      v
                             CANONICAL STORE
                          SQLite / Parquet V4
                                      |
                           +----------+----------+
                           v                     v
                        Qdrant                 Neo4j
                    semantic projection    relationship projection
                           |                     |
                           +----------+----------+
                                      |
                                      v
                             DEEPSEEK R1 8B
                          background synthesis
                                [V4.1]
                                      |
                                      v
                    DETERMINISTIC ESCALATION POLICY
                                      |
                                      v
                             OPENCLAW / LUNA
                            senior reasoning
                                [V4.1]
                                      |
                                      v
                           REACT / COPILOT
```

---

## 7. Evidence Acquisition Plane

The V4.2 Evidence Acquisition Plane owns:

- provider orchestration;
- provider health;
- authentication boundary;
- incremental cursors/watermarks;
- retries/backoff;
- provider-specific fallbacks;
- immutable raw capture;
- acquisition status;
- minimum-coverage evaluation.

It does **not** own:

- valuation;
- portfolio calculations;
- opportunity ranking;
- investment recommendation;
- LLM reasoning;
- trade execution.

---

## 8. Provider classes and authority model

V4.2 separates four concepts that must not be conflated:

### 8.1 Authority tier

Represents authority of the **underlying source**.

```text
TIER 0 — OFFICIAL DISCLOSURE / REGULATORY
TIER 1 — PRIMARY AUTHORITATIVE
TIER 2 — REPUTABLE MEDIA / RESEARCH
TIER 3 — GENERAL PUBLIC WEB
```

Examples:

**Tier 0**
- CVM official disclosures;
- official B3 disclosure content.

**Tier 1**
- issuer investor relations;
- BCB;
- IBGE;
- ANP;
- ANEEL;
- CADE;
- other official public agencies.

**Tier 2**
- Reuters;
- Valor;
- InfoMoney;
- Estadão;
- Exame;
- other reputable financial/general media.

**Tier 3**
- general public web content with no stronger authority class.

### 8.2 Source class

Examples:

```text
OFFICIAL_REGULATORY
OFFICIAL_EXCHANGE
OFFICIAL_ISSUER
OFFICIAL_AGENCY
INSTITUTIONAL_RESEARCH
FINANCIAL_MEDIA
GENERAL_MEDIA
GENERAL_WEB
```

### 8.3 Discovery channel

Represents **how the source was found**, not source authority.

Examples:

```text
CVM_RAD
CVM_OPEN_DATA
B3_PUBLIC
RSS
DIRECT_IR
DIRECT_AGENCY
SEARXNG_NEWS
SEARXNG_GENERAL
PUBLIC_WEB
```

A Reuters article found via SearXNG remains Tier 2 / FINANCIAL_MEDIA; SearXNG is only its discovery channel.

### 8.4 Transport reliability

Represents stability of the acquisition mechanism.

Examples:

```text
DOCUMENTED_OFFICIAL
STRUCTURED_PUBLIC
PUBLIC_STABLE
BEST_EFFORT
EXPERIMENTAL
```

This is deliberately independent from authority tier.

---

## 9. Official corporate-disclosure lane

### 9.1 CVM RAD / Download Múltiplo — PRIMARY CURRENT

Primary zero-cost source for current / near-current official company disclosures.

Known service:

```text
POST https://seguro.bmfbovespa.com.br/rad/download/SolicitaDownload.asp
```

Relevant request fields include:

```text
txtLogin
txtSenha
txtData
txtHora
txtDocumento=IPE
txtAssuntoIPE=SIM
```

The service returns XML with document metadata and document URLs.

Expected categories include:

- Fato Relevante;
- Comunicado ao Mercado;
- Aviso aos Acionistas;
- other IPE disclosures.

#### V4.2 semantics

CVM RAD is treated as an **incremental global disclosure feed**, not a per-ticker search engine.

```text
RAD poll
   ->
new documents in interval
   ->
CVM code / issuer mapping
   ->
one or more securities/tickers
```

### 9.2 CVM credentials

Credentials are runtime secrets:

```text
CVM_LOGIN
CVM_PASSWORD
```

They must never appear in:

- Git;
- source code;
- React payloads;
- logs;
- exception bodies;
- Copilot context;
- generated documentation containing real values.

Authentication failure is:

```text
AUTH_FAILED
```

never:

```text
NO_EVENTS
```

---

## 10. CVM Open Data IPE — BACKFILL / RECOVERY / RECONCILIATION

CVM Open Data IPE is complementary to RAD.

Primary responsibilities:

- historical backfill;
- long-term archive;
- recovery support;
- reconciliation;
- consistency checks;
- reconstruction of official-document history when live capture was unavailable.

Conceptually:

```text
CVM RAD
   = current/incremental capture

CVM Open Data
   = history/backfill/reconciliation
```

Open Data does not replace live first-seen capture for strict PIT semantics.

---

## 11. B3 public endpoints — OFFICIAL CONTENT, BEST-EFFORT TRANSPORT

Public endpoints used by B3 web applications may provide official content, including patterns such as:

```text
listedCompaniesProxy/CompanyCall/GetMaterialFacts
listedCompaniesProxy/CompanyCall/GetListedHeadLines
```

V4.2 classification:

```text
source authority     = OFFICIAL_EXCHANGE / Tier 0 when content is official
transport reliability = BEST_EFFORT
critical dependency   = NO
```

Rules:

- they may enrich/validate official evidence;
- endpoint changes must not stop UC-10;
- session/browser behavior may be required;
- retries/backoff/circuit-breaking are provider-local;
- failure produces degraded coverage, not a false no-event conclusion.

---

## 12. Open-web lane

CVM/B3 answer:

> what the company officially disclosed.

Open-web evidence answers:

> what is happening around the company, sector and market.

Examples:

- oil-price shocks;
- iron-ore/China demand;
- taxation;
- competitors;
- sector events;
- macroeconomics;
- geopolitics;
- regulation;
- supply chains;
- climate/weather;
- foreign flows;
- public institutional research;
- public broker/analyst material.

### 12.1 Direct free sources before search

Known direct sources should be preferred when available:

- official RSS/Atom;
- investor-relations feeds/pages;
- regulator/agency feeds/pages;
- public bulletins;
- structured public downloads.

SearXNG is most valuable for **discovery of unknown/current web evidence**.

---

## 13. SearXNG role in V4.2

SearXNG remains mandatory infrastructure for zero-cost open-web discovery.

It is **not** an authority source.

The V4.1 pattern:

```text
categories=news
time_range=day
```

is superseded as the sole production search contract.

### 13.1 Search strategy

Conceptually:

```text
SearXNG NEWS broad discovery
          |
          +--> adequate healthy results
          |
          +--> insufficient/degraded
                    |
                    v
              GENERAL fallback
                    |
                    v
            local time filtering
```

### 13.2 Local recency

Recency is controlled by the B3 backend, not trusted exclusively to search-engine time filters.

The backend preserves raw publication-time fields and normalizes them where possible.

Relative dates, ISO timestamps and unknown dates must remain distinguishable.

---

## 14. Incremental ingestion and watermark policy

Fixed “last N days” polling is not the primary V4.2 ingestion contract.

Each incremental provider maintains provider-specific state:

```text
last_successful_cursor / watermark
              |
              v
        safety overlap
              |
              v
         next window
              |
              v
     idempotent ingestion
              |
              v
        new watermark
```

The system should prefer at-least-once acquisition plus deterministic deduplication over the risk of missing a boundary record.

The exact overlap duration is implementation policy, not frozen in this document.

---

## 15. CVM RAD downtime / replay semantics

RAD windows must respect provider constraints.

If a period is missed:

```text
missed interval
    ->
replay in provider-supported windows
    ->
Open Data reconciliation
    ->
mark recovery quality explicitly
```

A recovered historical record is not automatically equivalent to an item observed live.

V4.2 therefore distinguishes PIT quality.

---

## 16. Point-in-Time time model

Do not collapse different time meanings.

Canonical evidence should preserve, where available:

```text
reference_at
published_at
first_seen_at
observed_at
retrieved_at
ingested_at
```

Provider raw values must remain auditable.

### 16.1 CVM DataRef

CVM `DataRef` must not be blindly interpreted as publication time.

It should map to a reference-time field unless provider documentation and observed payload prove publication semantics.

### 16.2 PIT status

Prefer an explicit temporal-quality classification:

```text
OBSERVED_LIVE
RECOVERED_LATE
HISTORICAL_RECONSTRUCTION
UNKNOWN
```

rather than a single `point_in_time_safe: true/false` flag.

---

## 17. Issuer Registry

Official disclosures belong to an issuer, not necessarily to one ticker.

V4.2 introduces an explicit issuer identity concept:

```text
Issuer
-----------------
issuer_id
cvm_code
cnpj
legal_name
trading_name

Security / Instrument
-----------------
instrument_id
ticker
issuer_id
asset_type
```

Example:

```text
CVM disclosure
      |
      v
issuer PETROBRAS
      |
   +--+--+
   v     v
 PETR3  PETR4
```

The registry is canonical structured data and must remain deterministic.

---

## 18. Canonical Evidence — evolve, do not duplicate

The repository already contains the canonical V4 evidence contract:

```text
src/b3_agent/knowledge/evidence.py
Evidence
EvidenceMetadata
```

V4.2 must evolve this contract instead of creating a parallel evidence type.

Existing fields remain valid, including:

- evidence_id;
- document_id;
- source;
- published_at;
- retrieved_at;
- ticker_refs;
- sector_refs;
- event_refs;
- source_quality;
- confidence;
- validity interval;
- retention;
- decay;
- content_hash;
- source_url.

V4.2 adds or standardizes concepts such as:

```text
issuer_ref
cvm_code
provider_record_id
source_class
authority_tier
discovery_channel
transport_reliability

reference_at
first_seen_at
observed_at
timestamp_precision / parse_method

source_status
acquisition_status
pit_status

materiality
materiality_reason
materiality_policy_version
```

Provider-specific metadata may continue using the existing extensible metadata mechanism where appropriate.

---

## 19. Evidence and Event are distinct

V4.2 freezes this semantic distinction:

```text
Evidence = observed artifact/document/source
Event    = normalized fact supported by one or more Evidence records
```

Example:

```text
CVM Fato Relevante ---+
Reuters ---------------+--> Event: acquisition X
Valor -----------------+
Issuer RI -------------+
```

Evidence remains immutable/auditable.

Events are derived and traceable to supporting evidence.

---

## 20. Immutable raw landing

External payloads used for material evidence should be retained according to lifecycle policy whenever technically practical.

Examples:

- CVM XML response metadata;
- official document bytes or immutable reference/hash;
- normalized web metadata;
- fetched public document text/hash.

RAW data is append-only / immutable.

A changed document creates another observation/version; it must not silently overwrite history.

---

## 21. Deduplication and event clustering

### 21.1 Deterministic deduplication

Primary dedup dimensions:

- provider record ID;
- canonical URL;
- normalized URL with tracking parameters removed;
- content hash;
- normalized title/headline;
- issuer + document/category + reference time.

### 21.2 Semantic clustering

The existing 768d embedding/RAG infrastructure may optionally cluster multiple articles about the same event.

Semantic clustering is a **derived aid**, not identity authority.

A cluster must preserve every source reference.

---

## 22. Materiality Engine

Materiality is determined **before DeepSeek**.

It is:

- deterministic;
- source-aware;
- versioned;
- auditable.

### 22.1 Official disclosures bypass generic web heuristics

Examples:

```text
CVM category == "Fato Relevante"
    -> MATERIAL by deterministic rule
    -> reason = OFFICIAL_FATO_RELEVANTE
```

No keyword match is required.

Other categories such as:

- Comunicado ao Mercado;
- Aviso aos Acionistas;

use their own deterministic policies.

### 22.2 Web evidence

Web evidence may use:

- entity/issuer match;
- freshness;
- source class;
- event classifier;
- deterministic terms/rules;
- corroboration;
- direct portfolio/sector relevance.

### 22.3 Materiality states

```text
MATERIAL
CANDIDATE
NON_MATERIAL
```

Suggested behavior:

```text
MATERIAL
    -> DeepSeek

CANDIDATE
    -> bounded DeepSeek review if policy allows

NON_MATERIAL
    -> persist; no LLM required
```

DeepSeek does not become canonical authority for materiality.

---

## 23. Coverage Contract

Acquisition success and evidence conclusion are separate dimensions.

### 23.1 Acquisition status

```text
SUCCESS
PARTIAL
DEGRADED
EMPTY
FAILED
AUTH_FAILED
```

### 23.2 Evidence conclusion

```text
MATERIAL_FOUND
NO_MATERIAL_FOUND
COVERAGE_INSUFFICIENT
```

### 23.3 Critical invariant

> **Absence of evidence may only become NO_MATERIAL_FOUND when the minimum required coverage contract has been satisfied.**

Examples:

```text
SearXNG results = 0
engine parsing errors present
        ->
COVERAGE_INSUFFICIENT
```

not:

```text
NO_MATERIAL_FOUND
```

---

## 24. Provider Result Envelope

Every provider call should return an operational envelope conceptually containing:

```text
provider
started_at
completed_at
query/window/cursor
status
raw_result_count
normalized_result_count
errors[]
warnings[]
fallback_used
next_cursor
coverage_metadata
```

SearXNG-specific envelope may include:

```text
unresponsive_engines[]
news_result_count
general_fallback_result_count
dated_result_count
```

CVM-specific envelope may include:

```text
auth_status
window_start
window_end
document_count
next_watermark
```

---

## 25. Full-document enrichment

Search snippets are discovery evidence, not sufficient context for every material event.

For MATERIAL/CANDIDATE evidence, V4.2 should prefer:

```text
official original document
        >
original publisher page
        >
search snippet
```

If only the snippet is available:

```text
content_status = SNIPPET_ONLY
```

No paywall bypass is allowed.

---

## 26. Canonical storage and projections

V4.2 preserves the V4 storage philosophy.

### 26.1 SQLite / Parquet

Canonical operational/structured truth:

- provider execution state;
- watermarks/cursors;
- issuer registry;
- evidence metadata;
- normalized events;
- evidence-event relationships;
- materiality decision/reason/version;
- PIT observation history.

### 26.2 RAW

Immutable files / Parquet / document artifacts as appropriate.

### 26.3 Qdrant

Semantic projection:

- evidence chunks;
- documents;
- event similarity;
- semantic retrieval.

### 26.4 Neo4j

Relationship projection:

- issuer;
- security;
- event;
- sector;
- commodity;
- regulator;
- executive/counterparty where supported;
- evidence supporting event.

Neither Qdrant nor Neo4j is the canonical source of truth.

---

## 27. DeepSeek and OpenClaw flow

The V4.1 reasoning hierarchy remains.

```text
Canonical Evidence Bundle
        |
        v
DeepSeek R1 local
structured dossier
        |
        v
Deterministic escalation policy
        |
        +--> stop
        |
        +--> OpenClaw / Luna senior reasoning
```

DeepSeek may:

- summarize evidence;
- identify contradictions;
- identify risks/catalysts;
- propose relationships;
- request escalation.

DeepSeek may not:

- fabricate evidence;
- change canonical prices;
- override deterministic materiality silently;
- become evidence authority.

OpenClaw/Luna may perform senior reasoning only over validated context/evidence.

---

## 28. MarketIntelligenceAgent boundary change

Current code includes:

```text
OpenAIWebResearchClient
    -> OpenAI Responses API
    -> hosted web_search
```

In V4.2 this is **superseded as the production acquisition path**.

The future production boundary is:

```text
Zero-Cost Evidence Acquisition Plane
        ->
Canonical Evidence Bundle
        ->
Market Intelligence reasoning
```

Reasoning and acquisition must not remain coupled in one hosted-search call.

This architectural change does not require immediate code deletion; implementation must migrate call sites safely.

---

## 29. Security model for external evidence

All content acquired from:

- SearXNG;
- RSS;
- public web;
- investor-relations pages;
- public documents;

must be treated as **untrusted data**.

Provider/fetch layers should enforce, where applicable:

- public HTTP(S) only;
- no localhost/private/metadata targets;
- redirect revalidation;
- timeouts;
- response-size limits;
- cache;
- rate limiting;
- identifiable User-Agent;
- bounded retries;
- circuit breaker for repeated provider failure;
- no paywall bypass;
- no execution of page instructions.

LLMs receive external content as read-only evidence, never as instructions.

---

## 30. Observability

V4.2 observability is first-class.

Per provider/run:

```text
provider
ticker/issuer scope
query/window
latency
raw_results
normalized_results
dated_results
recent_results
duplicates_removed
material_candidates
documents_fetched
provider_errors
engine_errors
fallback_used
coverage_status
```

Global indicators may include:

```text
official coverage rate
open-web coverage rate
SearXNG empty rate
SearXNG degraded-engine rate
fallback rate
CVM authentication failures
CVM gap-recovery count
material events detected
DeepSeek calls
DeepSeek failures
OpenClaw escalations
```

---

## 31. Explicitly superseded V4.1 behaviors

The following are superseded by V4.2:

1. OpenAI hosted `web_search` as the production acquisition mechanism for Market Intelligence.
2. `SearXNG news + time_range=day` as the sole/primary production news contract.
3. Treating any empty search path as `skipped_no_material_events`.
4. Applying generic web static-domain filters to official B3 disclosure providers.
5. Treating search snippets as sufficient evidence for all material events.
6. Using fixed last-N-days search as the primary incremental ingestion model.

---

## 32. Existing ADR impact

### ADR-0010 — Market Intelligence Agent with Web Research

Its hosted OpenAI web-search acquisition decision becomes superseded by V4.2 once implementation is complete.

A follow-up ADR should record:

```text
free provider acquisition
    ->
canonical Evidence
    ->
Market Intelligence reasoning
```

### ADR-0012 — RAG Evidence & Metadata Contract

Preserved and extended.

### ADR-0017 — RAG PIT retrieval

Preserved and strengthened by first-seen / observation semantics.

---

## 33. Reinterpretation of the V4.1 20-stock pilot

The 20-stock pilot remains useful but must be recorded accurately:

```text
ROUTING                    PASS
STRUCTURED MARKET DATA     PASS
BATCH EXECUTION            PASS
RESOURCE BEHAVIOR          PASS
UC-10 SEARCH COVERAGE      NOT VALIDATED
DEEPSEEK REAL EVIDENCE     NOT EXERCISED
OPENCLAW REAL ESCALATION   NOT EXERCISED
```

The result must not be presented as proof that the 20 companies had no material events.

---

## 34. V4.2 validation strategy

V4.2 acceptance must not depend on chance that a material event happens during a live pilot.

Two acceptance tracks are required.

### 34.1 Live Coverage Pilot

A representative multi-stock universe validates:

- CVM current-feed ingestion;
- SearXNG open-web discovery;
- provider health;
- coverage states;
- timestamp normalization;
- issuer/ticker mapping;
- deduplication;
- no false NO_MATERIAL result under provider failure;
- zero paid API usage.

### 34.2 Historical Real-Evidence Replay

Use at least one **real, previously published official material disclosure**.

Replay:

```text
real CVM evidence
      ->
normalization
      ->
PIT handling
      ->
materiality
      ->
DeepSeek
      ->
deterministic escalation
      ->
OpenClaw
```

No synthetic material event is needed for the final acceptance path.

---

## 35. Migration plan

Implementation should be phased.

### Phase A — contracts and observability

- provider result envelope;
- acquisition/evidence status enums;
- coverage contract;
- expanded canonical evidence metadata;
- tests only / no provider cutover.

### Phase B — SearXNG resiliency

- remove provider-time-range dependence as primary freshness mechanism;
- news/general fallback;
- relative/ISO timestamp normalization;
- engine-error capture;
- local recency;
- persist per-ticker acquisition counters.

### Phase C — issuer registry

- issuer identity;
- CVM code;
- issuer-to-security/ticker mapping;
- tests for multi-class companies.

### Phase D — CVM RAD

- authenticated provider;
- <= provider-supported windows;
- watermark/cursor;
- append-only first-seen history;
- XML metadata normalization;
- official-materiality rules.

### Phase E — CVM Open Data

- historical/backfill ingestion;
- reconciliation;
- recovery status/PIT quality.

### Phase F — B3 best-effort

- provider isolated from core;
- retry/backoff;
- no critical dependency;
- enrichment/validation role only.

### Phase G — evidence/event integration

- dedup;
- event cluster;
- original-document enrichment;
- canonical store;
- Qdrant/Neo4j projections.

### Phase H — reasoning cutover

- MarketIntelligenceAgent consumes canonical Evidence Bundle;
- hosted paid web-search acquisition removed from production path;
- DeepSeek/OpenClaw unchanged as reasoning tiers.

### Phase I — acceptance

- unit tests;
- integration tests;
- live coverage pilot;
- real historical material-event replay;
- backend full validation.

---

## 36. Acceptance criteria for V4.2

V4.2 implementation is acceptable when all items below are true:

- zero paid API dependency for news/events/market-intelligence evidence acquisition;
- CVM RAD is primary current official-disclosure provider;
- CVM Open Data supports historical/backfill/reconciliation;
- B3 public endpoints are optional/best-effort;
- SearXNG remains available for open-web discovery;
- SearXNG failures do not become false NO_MATERIAL conclusions;
- provider acquisition state is observable;
- minimum coverage contract is enforced;
- official disclosures bypass generic web static filtering;
- Fato Relevante is deterministically material by source/category rule;
- issuer/CVM-code/ticker mapping is deterministic;
- published/reference/first-seen/retrieved semantics are not collapsed;
- evidence history is append-only for PIT-sensitive observations;
- existing Evidence contract is reused/evolved rather than duplicated;
- Evidence and Event remain distinct;
- Qdrant/Neo4j remain projections;
- DeepSeek remains local/background;
- OpenClaw/Luna remains senior escalation;
- deterministic market/portfolio authority is unchanged;
- no autonomous execution is introduced;
- live coverage pilot passes;
- historical real-evidence replay exercises DeepSeek and OpenClaw;
- existing backend regression suite remains green.

---

## 37. Non-goals

V4.2 does not attempt to:

- replace deterministic market-data providers;
- replace options-chain infrastructure;
- rank investment opportunities inside the evidence layer;
- infer authoritative prices from news;
- use paid news APIs;
- bypass paywalls;
- scrape authenticated private content;
- perform autonomous trading;
- make DeepSeek/OpenClaw the source of truth;
- redesign the React navigation;
- reopen V4.0/V4.1 storage authority decisions.

---

## 38. Frozen V4.2 decisions

The following are approved architecture decisions:

1. **ZERO-PAID-INTELLIGENCE** is a non-negotiable invariant for news/events/market-intelligence evidence acquisition.
2. **CVM RAD / Download Múltiplo** is the primary current official-disclosure lane.
3. **CVM Open Data IPE** is the backfill/history/reconciliation lane.
4. **B3 public website endpoints** are official-content, best-effort-transport and never critical dependencies.
5. **SearXNG remains** the primary zero-cost open-web discovery mechanism.
6. Direct **RSS / issuer RI / public agency sources** are preferred when known.
7. The existing V4 **Evidence** contract is evolved, not duplicated.
8. **Evidence and Event are distinct concepts.**
9. **Authority tier, source class, discovery channel and transport reliability are independent dimensions.**
10. **Issuer identity / CVM code mapping** becomes explicit.
11. **Materiality is deterministic, source-aware and versioned before DeepSeek.**
12. **Coverage is a contract.**
13. **Provider failure cannot be represented as “no material event”.**
14. **CVM observations are append-only for PIT-sensitive history.**
15. **Recency is enforced locally by B3**, not delegated exclusively to search-provider filters.
16. **Hosted paid web search is superseded as production acquisition.**
17. **DeepSeek/OpenClaw roles from V4.1 remain unchanged.**
18. **V4.0/V4.1 deterministic authority remains unchanged.**
19. **Human remains final decision authority.**
20. **No autonomous execution is introduced.**

---

## 39. Implementation gate

This document approves the architecture.

Implementation must proceed on a dedicated implementation branch/PR, in small phases, with tests at each phase.

No implementation change is considered accepted merely because code compiles.

The required progression is:

```text
ARCHITECTURE V4.2
      ->
contracts/tests
      ->
provider implementation
      ->
integration tests
      ->
live coverage validation
      ->
historical real-evidence replay
      ->
backend regression validation
      ->
V4.2 implementation freeze
```
