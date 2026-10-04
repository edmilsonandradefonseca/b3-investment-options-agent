"""Read qualified B3 research projections before collecting new research.

No financial facts or Learning authority are inferred from semantic scores.
The existing Qdrant/Neo4j projections remain read models, not new truth stores.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import math
import os
from typing import Any, Callable

from b3_agent.knowledge.graph_schema import EntityType, RelationType
from b3_agent.knowledge.vector_store import MetadataFilter
from b3_agent.research_events import ResearchEvent

POLICY = "stored-research-v1"


def _timestamp(value: Any) -> datetime | None:
    try:
        if isinstance(value, datetime):
            result = value
        elif isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value):
            result = datetime.fromtimestamp(value, timezone.utc)
        elif isinstance(value, str):
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            return None
        return result if result.tzinfo is not None and result.utcoffset() is not None else None
    except (ValueError, OverflowError, OSError):
        return None


def _temporal_reason(published, available, valid_from, valid_to, as_of, max_age):
    if published is None or available is None:
        return "AVAILABILITY_OR_PUBLICATION_UNKNOWN"
    if published > as_of or available > as_of or (valid_from and valid_from > as_of):
        return "FUTURE_AT_CUTOFF"
    if valid_to and (valid_to < as_of or (valid_from and valid_to < valid_from)):
        return "OUTSIDE_VALIDITY"
    if as_of - published > max_age:
        return "STALE_FOR_CURRENT_RESEARCH"
    return None


def _vector_source():
    from qdrant_client import QdrantClient
    from b3_agent.knowledge.embeddings import HttpEmbeddingProvider
    from b3_agent.knowledge.qdrant_store import QdrantVectorStore
    from b3_agent.knowledge.retrieval import VectorEvidenceRetriever

    client = QdrantClient(url=os.getenv("B3_QDRANT_URL", "http://127.0.0.1:6333"), timeout=3)
    try:
        store = QdrantVectorStore(client=client, collection_name="b3_evidence_768_hybrid",
                                  vector_size=768, hybrid=True, read_only=True)
        embeddings = HttpEmbeddingProvider(base_url=os.getenv("B3_EMBEDDING_URL", "http://127.0.0.1:8093"),
                                            dimensions=768, timeout=3)
        return VectorEvidenceRetriever(store, embeddings), client.close
    except Exception:
        client.close()
        raise


def _graph_source():
    from neo4j import GraphDatabase
    from b3_agent.knowledge.neo4j_store import Neo4jKnowledgeGraphStore
    from b3_agent.orchestration.runtime import _load_shared_env_value

    password = _load_shared_env_value("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("Neo4j credentials unavailable")
    driver = GraphDatabase.driver(os.getenv("B3_NEO4J_URI", "bolt://127.0.0.1:7687"),
        auth=(os.getenv("B3_NEO4J_USER", "neo4j"), password),
        connection_timeout=3, connection_acquisition_timeout=3,
        max_transaction_retry_time=0)
    return Neo4jKnowledgeGraphStore(driver, read_only=True), driver.close


class StoredResearchContextService:
    def __init__(self, *, vector_factory: Callable | None = None, graph_factory: Callable | None = None):
        self.vector_factory = vector_factory or _vector_source
        self.graph_factory = graph_factory or _graph_source

    def build(self, ticker: str, *, as_of: datetime, limit: int = 8,
              max_age: timedelta = timedelta(hours=48)) -> dict[str, Any]:
        ticker = ticker.strip().upper()
        if not ticker or len(ticker) > 30:
            raise ValueError("an explicit ticker is required")
        if not isinstance(as_of, datetime) or _timestamp(as_of) is None:
            raise ValueError("as_of must be timezone-aware")
        if not 1 <= limit <= 20 or max_age <= timedelta(0):
            raise ValueError("invalid stored research bounds")
        excluded = Counter()
        candidates: list[tuple[str, ResearchEvent]] = []
        backends: dict[str, str] = {}
        relations: list[dict[str, Any]] = []
        for backend, factory in (("qdrant", self.vector_factory), ("neo4j", self.graph_factory)):
            close = None
            try:
                source, close = factory()
                if backend == "qdrant":
                    hits = source.retrieve_results(f"{ticker} resultados fatos relevantes notícias riscos",
                        top_k=limit * 5, metadata_filter=MetadataFilter(ticker=ticker, topic="news", published_before=as_of))
                    for hit in hits:
                        m = hit.metadata
                        tickers = m.get("ticker_refs")
                        if not isinstance(tickers, (list, tuple)) or ticker not in tickers or m.get("topic") != "news":
                            excluded["TICKER_OR_TOPIC_MISMATCH"] += 1
                            continue
                        if m.get("source_quality") not in {"provider", "official", "primary"}:
                            excluded["UNQUALIFIED_SOURCE"] += 1
                            continue
                        published, available = _timestamp(m.get("published_at")), _timestamp(m.get("retrieved_at"))
                        start, end = _timestamp(m.get("valid_from")), _timestamp(m.get("valid_to"))
                        if any(m.get(key) is not None and _timestamp(m[key]) is None for key in ("valid_from", "valid_to")):
                            excluded["INVALID_VALIDITY_TIMESTAMP"] += 1
                            continue
                        reason = _temporal_reason(published, available, start, end, as_of, max_age)
                        if reason:
                            excluded[reason] += 1
                            continue
                        ref = m.get("source")
                        if not isinstance(ref, str) or not ref.strip() or not hit.content.strip():
                            excluded["MISSING_SOURCE_OR_CONTENT"] += 1
                            continue
                        extra = m.get("extra") if isinstance(m.get("extra"), dict) else {}
                        if extra.get("chunk_index", 0) != 0:
                            excluded["NON_INITIAL_NEWS_CHUNK"] += 1
                            continue
                        lines = hit.content.split("\n", 1)
                        event = ResearchEvent(str(m.get("document_id") or hit.evidence_id), ticker,
                            str(extra.get("event_type") or "NEWS"), published, available,
                            lines[0][:600], lines[1].strip()[:800] if len(lines) > 1 else None,
                            str(extra.get("source_name") or ref), ref, extra.get("relevance"))
                        candidates.append((backend, event))
                else:
                    self._graph_events(source, ticker, as_of, max_age, limit, candidates, relations, excluded)
                backends[backend] = "READ_OK"
            except Exception as exc:
                # Driver errors may contain connection/user data. Expose only the type.
                backends[backend] = f"UNAVAILABLE:{type(exc).__name__}"
            finally:
                if close:
                    try:
                        close()
                    except Exception:
                        backends[backend] = "UNAVAILABLE:CLOSE_FAILED"
        # One event projected to both memories is one observation, not two votes.
        unique: dict[str, tuple[ResearchEvent, set[str]]] = {}
        conflicting_refs: set[str] = set()
        for backend, event in candidates:
            previous = unique.get(event.source_ref)
            if previous and (previous[0].published_at != event.published_at or previous[0].headline != event.headline):
                conflicting_refs.add(event.source_ref)
                excluded["CONFLICTING_PROJECTIONS"] += 1
            elif previous:
                previous[1].add(backend)
            else:
                unique[event.source_ref] = (event, {backend})
        ordered = sorted((v for ref, v in unique.items() if ref not in conflicting_refs),
                         key=lambda v: (v[0].published_at, v[0].event_id), reverse=True)
        relations = [r for r in relations if r["source_ref"] not in conflicting_refs]
        events = [{**asdict(event), "retrieved_from": sorted(origins)} for event, origins in ordered[:limit]]
        return {"policy_version": POLICY, "ticker": ticker, "as_of": as_of.isoformat(),
                "status": "AVAILABLE" if events else "NO_ADMISSIBLE_RECENT_RESEARCH",
                "authority": "source_linked_research_projection_only",
                "max_age_hours": max_age.total_seconds() / 3600,
                "events": events, "relations": relations[:20], "backends": backends,
                "excluded": dict(excluded), "omitted_event_count": max(0, len(ordered) - limit),
                "source_refs": list(dict.fromkeys([e["source_ref"] for e in events] + [r["source_ref"] for r in relations[:20]])),
                "limitations": ["Recent retrieved research is not exhaustive event coverage, valuation, probability or canonical learning."]}

    @staticmethod
    def _graph_events(graph, ticker, as_of, max_age, limit, candidates, relations, excluded):
        seeds = graph.find_entities(canonical_id=ticker, limit=4)
        seen = set()
        for seed in seeds:
            if seed.entity_type not in {EntityType.INSTRUMENT, EntityType.STOCK, EntityType.COMPANY, EntityType.INDEX, EntityType.ETF}:
                continue
            if seed.canonical_id != ticker or _timestamp(seed.as_of) is None or seed.as_of > as_of:
                continue
            edges = graph.get_relations(source_id=seed.entity_id, limit=20)
            edges += graph.get_relations(target_id=seed.entity_id, limit=20)
            for edge in edges:
                key = (edge.source_id, edge.relation, edge.target_id)
                if key in seen:
                    continue
                seen.add(key)
                if seed.entity_id not in {edge.source_id, edge.target_id}:
                    continue
                other = edge.target_id if edge.source_id == seed.entity_id else edge.source_id
                event = graph.get_entity(other)
                if event is None or event.entity_type != EntityType.MARKET_EVENT:
                    continue
                if edge.relation not in {RelationType.IMPACTS, RelationType.AFFECTS, RelationType.ABOUT}:
                    continue
                if _timestamp(edge.as_of) is None or edge.as_of > as_of:
                    excluded["GRAPH_EDGE_AVAILABILITY_UNKNOWN_OR_FUTURE"] += 1
                    continue
                if any(getattr(item, field) is not None and _timestamp(getattr(item, field)) is None
                       for item in (seed, edge, event) for field in ("as_of", "valid_from", "valid_to")):
                    excluded["INVALID_VALIDITY_TIMESTAMP"] += 1
                    continue
                if any((item.valid_from is not None and item.valid_from > as_of) or
                       (item.valid_to is not None and item.valid_to < as_of) for item in (seed, edge, event)):
                    excluded["OUTSIDE_VALIDITY"] += 1
                    continue
                published, available = _timestamp(event.valid_from), _timestamp(event.as_of)
                reason = _temporal_reason(published, available, _timestamp(edge.valid_from),
                                         _timestamp(event.valid_to), as_of, max_age)
                if edge.valid_to is not None and (_timestamp(edge.valid_to) is None or edge.valid_to < as_of):
                    reason = "OUTSIDE_VALIDITY"
                if reason:
                    excluded[reason] += 1
                    continue
                if event.provenance != "runtime_projection:v1" or not event.source_ref:
                    excluded["UNQUALIFIED_SOURCE"] += 1
                    continue
                candidates.append(("neo4j", ResearchEvent(event.canonical_id or event.entity_id, ticker,
                    str(event.properties.get("event_type") or "NEWS"), published, available,
                    event.name[:600], str(event.properties["summary"])[:800] if event.properties.get("summary") else None,
                    str(event.properties.get("source_name") or event.source_ref), event.source_ref,
                    event.properties.get("relevance"))))
                relations.append({"source_id": edge.source_id, "relation": edge.relation.value,
                    "target_id": edge.target_id, "source_ref": event.source_ref,
                    "available_at": edge.as_of.isoformat()})
                if len(candidates) >= limit * 5:
                    return
