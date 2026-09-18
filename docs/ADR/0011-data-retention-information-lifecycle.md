# ADR 0011 — Data Retention & Information Lifecycle

**Status:** Accepted  
**Date:** 2026-09-17  
**Scope:** Market data, options data, market intelligence and persistent knowledge

## Decision

The B3 agent uses **rolling retention windows** for high-volume market data and a
separate lifecycle/decay policy for information used by RAG and the Knowledge Graph.

### Retention policy

| Data class | Physical retention | Lifecycle rule |
|---|---:|---|
| Stock market observations | **360 days** | Rolling window |
| Detailed option market observations | **90 days** | Rolling window |
| Raw/normalized market evidence | **90 days** | Purge after retention window |
| Market events | No fixed expiry | Keep while relevant/active |
| Investment decisions | Permanent | Audit record |
| Persistent human knowledge | Permanent | Obsidian/source knowledge |
| Portfolio/transaction records | Permanent | Audit/portfolio history |

The rolling window is evaluated against `last_updated`, not the creation time of
the storage record. A record older than the retention window is a purge candidate.

## Freshness decay

Physical retention and retrieval priority are separate concerns. Records may become
less relevant before they are physically deleted.

Freshness is deterministic and uses an exponential half-life:

```text
freshness = exp(-ln(2) * age_days / half_life_days)
```

Initial profiles:

| Profile | Half-life |
|---|---:|
| FAST | 7 days |
| MEDIUM | 30 days |
| SLOW | 90 days |
| STRUCTURAL | 365 days |
| PERMANENT | no decay |

The lifecycle engine currently assigns FAST to options/evidence, SLOW to stock
market observations, MEDIUM to market events, and PERMANENT to decisions and
persistent knowledge.

## Critical rule: do not delete knowledge just because evidence is old

The system distinguishes:

```text
NEWS / EVIDENCE
      ↓
MARKET EVENT / INTELLIGENCE
      ↓
RAG + KNOWLEDGE GRAPH
```

An article can expire while a structured market event remains in the KG. An active
event must not be purged by age alone. New evidence can update `last_updated` and
reactivate or extend the useful lifetime of an event.

## Purge execution

The lifecycle engine is deliberately deterministic and side-effect free. It produces
`LifecycleAssessment` objects and purge candidates. A later storage-specific purge
job may consume these candidates for SQLite, vector storage or Neo4j maintenance.

The purge job must:

1. use an explicit `as_of` timestamp;
2. delete only records classified as purge candidates;
3. never delete permanent classes automatically;
4. never delete an ACTIVE market event by age alone;
5. emit an auditable purge summary;
6. support dry-run mode before physical deletion.

## Why 360 days for stocks?

A one-year rolling price window is sufficient for the MVP dashboard to display and
analyze a full annual price curve while bounding storage growth. Longer historical
analysis can later be provided by a separate archive or on-demand provider without
forcing the operational database to retain unlimited observations.

## Why 90 days for market information?

Market news and evidence have substantially faster information decay and can create
large volumes. Ninety days provides a useful recent-information window while keeping
the operational knowledge base bounded. Durable value is retained through structured
market events, decisions and persistent knowledge rather than every old article.

## Non-goals

- No automatic deletion of Obsidian human knowledge.
- No automatic deletion of investment decisions.
- No LLM-based decision about whether a record may be purged.
- No assumption that every old event is irrelevant.
