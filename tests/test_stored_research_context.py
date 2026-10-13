from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from b3_agent import server
from b3_agent.intelligence import stored_research, workspace_context
from b3_agent.intelligence.stored_research import StoredResearchContextService
from b3_agent.knowledge.graph_schema import GraphEntity, GraphRelation, EntityType, RelationType
from b3_agent.knowledge.in_memory_graph import InMemoryKnowledgeGraphStore
from b3_agent.knowledge.vector_store import VectorSearchResult
from test_workspace_intelligence_context import FakeAssetEvidenceService, FakeMacroRepository, FakeNewsProvider

NOW = datetime(2026, 10, 2, 15, tzinfo=timezone.utc)
PUB = NOW - timedelta(hours=1)
REF = "https://ri.example.test/event/1"


def hit(**changes):
    metadata = dict(ticker_refs=["RENT3"], topic="news", source=REF,
        source_quality="provider", published_at=PUB.timestamp(), retrieved_at=PUB.timestamp(),
        valid_from=PUB.timestamp(), valid_to=None, document_id=REF,
        extra={"event_type": "NEWS", "source_name": "RI"})
    metadata.update(changes)
    return VectorSearchResult(chunk_id="chunk:1", evidence_id="NEWS:1", score=0.9,
                              content="RENT3 publica guidance\n\nTexto da fonte.", metadata=metadata)


class Vector:
    def __init__(self, records):
        self.records = records
        self.calls = []
    def retrieve_results(self, query, **kwargs):
        self.calls.append((query, kwargs))
        return self.records


def graph():
    store = InMemoryKnowledgeGraphStore()
    instrument = GraphEntity("INSTR:RENT3", EntityType.INSTRUMENT, "RENT3", canonical_id="RENT3", as_of=PUB)
    event = GraphEntity("EVENT:1", EntityType.MARKET_EVENT, "RENT3 publica guidance", canonical_id=REF,
        source_ref=REF, provenance="runtime_projection:v1", as_of=PUB, valid_from=PUB,
        properties={"summary": "Texto da fonte.", "event_type": "NEWS", "source_name": "RI"})
    store.upsert_entity(instrument)
    store.upsert_entity(event)
    store.upsert_relation(GraphRelation(event.entity_id, RelationType.IMPACTS, instrument.entity_id,
                                       source_ref=REF, as_of=PUB))
    return store


def service(records=(), kg=None):
    vector = Vector(records)
    closed = []
    instance = StoredResearchContextService(
        vector_factory=lambda: (vector, lambda: closed.append("vector")),
        graph_factory=lambda: (kg or InMemoryKnowledgeGraphStore(), lambda: closed.append("graph")))
    return instance, vector, closed


def test_exact_pit_research_reuses_projections_once_and_preserves_provenance():
    instance, vector, closed = service([hit(), hit()], graph())
    result = instance.build("rent3", as_of=NOW)
    assert len(result["events"]) == 1
    assert result["events"][0]["retrieved_from"] == ["neo4j", "qdrant"]
    assert result["events"][0]["available_at"] == PUB
    assert result["source_refs"] == [REF]
    assert result["relations"][0]["target_id"] == "INSTR:RENT3"
    assert vector.calls[0][1]["metadata_filter"].ticker == "RENT3"
    assert vector.calls[0][1]["metadata_filter"].topic == "news"
    assert closed == ["vector", "graph"]


@pytest.mark.parametrize("metadata,reason", [
    ({"ticker_refs": ["VALE3"]}, "TICKER_OR_TOPIC_MISMATCH"),
    ({"topic": "learning"}, "TICKER_OR_TOPIC_MISMATCH"),
    ({"source_quality": "llm"}, "UNQUALIFIED_SOURCE"),
    ({"retrieved_at": None}, "AVAILABILITY_OR_PUBLICATION_UNKNOWN"),
    ({"retrieved_at": (NOW + timedelta(seconds=1)).timestamp()}, "FUTURE_AT_CUTOFF"),
    ({"published_at": (NOW + timedelta(seconds=1)).timestamp()}, "FUTURE_AT_CUTOFF"),
    ({"published_at": (NOW - timedelta(days=3)).timestamp()}, "STALE_FOR_CURRENT_RESEARCH"),
    ({"valid_to": (NOW - timedelta(minutes=1)).timestamp()}, "OUTSIDE_VALIDITY"),
    ({"valid_to": "bad date"}, "INVALID_VALIDITY_TIMESTAMP"),
    ({"source": ""}, "MISSING_SOURCE_OR_CONTENT"),
])
def test_unqualified_future_stale_and_other_subjects_do_not_suppress_collection(metadata, reason):
    instance, _, _ = service([hit(**metadata)])
    result = instance.build("RENT3", as_of=NOW)
    assert result["events"] == []
    assert result["excluded"][reason] == 1


def test_conflicting_projections_remain_a_gap_not_extra_confirmation():
    kg = graph()
    kg.upsert_entity(replace(kg.get_entity("EVENT:1"), name="Outra versão do guidance"))
    instance, _, _ = service([hit()], kg)
    result = instance.build("RENT3", as_of=NOW)
    assert result["events"] == result["relations"] == result["source_refs"] == []
    assert result["excluded"]["CONFLICTING_PROJECTIONS"] == 1


def test_graph_requires_exact_relation_availability_and_rejects_future_edges():
    kg = graph()
    edge = kg.get_relations(target_id="INSTR:RENT3")[0]
    kg.upsert_relation(replace(edge, as_of=NOW + timedelta(minutes=1)))
    instance, _, _ = service(kg=kg)
    result = instance.build("RENT3", as_of=NOW)
    assert not result["events"]
    assert result["excluded"]["GRAPH_EDGE_AVAILABILITY_UNKNOWN_OR_FUTURE"] == 1
    assert instance.build("VALE3", as_of=NOW)["events"] == []


def test_backend_failure_is_isolated_sanitized_and_does_not_fabricate_empty_truth():
    def unavailable():
        raise RuntimeError("private credential must not be exposed")
    instance, _, _ = service([hit()])
    instance.graph_factory = unavailable
    result = instance.build("RENT3", as_of=NOW)
    assert len(result["events"]) == 1
    assert result["backends"]["neo4j"] == "UNAVAILABLE:RuntimeError"
    assert "private credential" not in str(result)


class CountingNews(FakeNewsProvider):
    def __init__(self): self.calls = []
    def search(self, ticker, **kwargs):
        self.calls.append(ticker)
        return super().search(ticker, **kwargs)


class Memory:
    def __init__(self): self.calls = []
    def build(self, ticker, *, as_of, **kwargs):
        self.calls.append((ticker, as_of))
        events = [{"ticker": ticker, "source_ref": f"stored:{ticker}", "headline": f"{ticker} existente",
                   "published_at": as_of - timedelta(hours=1), "available_at": as_of - timedelta(hours=1),
                   "retrieved_from": ["qdrant"]}] if ticker in {"ASAI3", "IBOV"} else []
        return {"events": events, "source_refs": [e["source_ref"] for e in events]}


def workspace(monkeypatch, tmp_path):
    monkeypatch.setattr(workspace_context, "settings", SimpleNamespace(data_dir=tmp_path))
    monkeypatch.setattr(workspace_context, "local_ticker_intelligence", lambda ticker: {})
    memory, news = Memory(), CountingNews()
    svc = workspace_context.WorkspaceIntelligenceContextService(stored_research_service=memory,
        asset_evidence_service=FakeAssetEvidenceService(), macro_repository=FakeMacroRepository(),
        news_provider=news, fallback_news_provider=CountingNews())
    return svc, memory, news


def test_inside_outside_comparison_uses_existing_research_then_fetches_only_missing_subject(monkeypatch, tmp_path):
    svc, memory, news = workspace(monkeypatch, tmp_path)
    result = svc.build(workspace="Strategy Lab", tickers=("ASAI3", "EMBR3", "ASAI3"), include_joao=False)
    assert news.calls == ["EMBR3"]
    assert [t for t, _ in memory.calls] == ["ASAI3", "EMBR3"]
    market = result.deterministic_context["market_analysis"]["tickers"]
    assert market["ASAI3"]["research_acquisition"]["reason"] == "STORED_EVENTS_REUSED"
    assert market["EMBR3"]["research_events"][0]["retrieved_from"] == ["external_research"]
    assert "stored:ASAI3" in result.source_refs


@pytest.mark.parametrize("mode,cutoff", [("stored_only", None), ("stored_first", NOW), ("refresh", NOW)])
def test_stored_only_and_historical_research_never_acquire_future_web_evidence(monkeypatch, tmp_path, mode, cutoff):
    svc, memory, news = workspace(monkeypatch, tmp_path)
    result = svc.build(workspace="Market Intelligence", tickers=("EMBR3",), include_joao=False,
                       research_mode=mode, history_as_of=cutoff)
    assert news.calls == []
    assert [t for t, _ in memory.calls] == ["EMBR3", "IBOV"]
    assert result.deterministic_context["market_analysis"]["tickers"]["EMBR3"]["research_events"] == []
    if cutoff: assert all(date == cutoff for _, date in memory.calls)


def test_explicit_refresh_collects_even_when_stored_research_exists(monkeypatch, tmp_path):
    svc, _, news = workspace(monkeypatch, tmp_path)
    result = svc.build(workspace="Strategy Lab", tickers=("ASAI3",), include_joao=False, research_mode="refresh")
    assert news.calls == ["ASAI3"]
    assert len(result.deterministic_context["market_analysis"]["tickers"]["ASAI3"]["research_events"]) == 2


def test_research_endpoint_is_stored_only_and_validates_before_connecting(monkeypatch):
    instance, vector, _ = service([hit()])
    monkeypatch.setattr(stored_research, "StoredResearchContextService", lambda: instance)
    client = TestClient(server.app)
    response = client.get("/intelligence/research-context", params={"ticker": "RENT3", "as_of": NOW.isoformat()})
    assert response.status_code == 200
    assert response.json()["events"][0]["available_at"] == PUB.isoformat()
    previous = len(vector.calls)
    for params in ({"ticker": ""}, {"ticker": "RENT3", "as_of": "2026-10-02"}, {"ticker": "RENT3", "limit": 21}):
        assert client.get("/intelligence/research-context", params=params).status_code == 422
    assert len(vector.calls) == previous


def test_qdrant_read_only_does_not_create_or_mutate_collections():
    from qdrant_client import QdrantClient
    from b3_agent.knowledge.qdrant_store import QdrantVectorStore
    client = QdrantClient(":memory:")
    with pytest.raises(RuntimeError, match="cannot create"):
        QdrantVectorStore(client=client, collection_name="missing", vector_size=8, read_only=True)
    assert not client.collection_exists("missing")
    QdrantVectorStore(client=client, collection_name="existing", vector_size=8)
    reader = QdrantVectorStore(client=client, collection_name="existing", vector_size=8, read_only=True)
    with pytest.raises(RuntimeError, match="cannot upsert"): reader.upsert((), ())
    with pytest.raises(RuntimeError, match="cannot delete"): reader.delete(())
    assert reader.count() == 0


def test_neo4j_read_only_skips_constraints_and_blocks_writes():
    from b3_agent.knowledge.neo4j_store import Neo4jKnowledgeGraphStore
    class Driver:
        def session(self): raise AssertionError("must not issue schema/write query")
    reader = Neo4jKnowledgeGraphStore(Driver(), read_only=True)
    kg = graph()
    event = kg.get_entity("EVENT:1")
    edge = kg.get_relations(target_id="INSTR:RENT3")[0]
    for call in (lambda: reader.upsert_entity(event), lambda: reader.upsert_relation(edge),
                 lambda: reader.delete_entity(event.entity_id), lambda: reader.delete_relation(edge)):
        with pytest.raises(RuntimeError, match="cannot mutate"): call()


def test_missing_modes_bounds_and_naive_cutoffs_fail_before_retrieval(monkeypatch, tmp_path):
    svc, memory, news = workspace(monkeypatch, tmp_path)
    for kwargs in ({"research_mode": "invent"}, {"history_as_of": "2026-10-01"},
                   {"news_limit": 100}):
        with pytest.raises(ValueError): svc.build(workspace="Strategy Lab", tickers=("RENT3",), **kwargs)
    assert memory.calls == news.calls == []


def test_workspace_task_subjects_include_outside_portfolio_tickers():
    request = server.OrchestratorRequest(task="Compare ASAI3 com EMBR3", context={"workspace": "Strategy Lab"})
    assert server._workspace_tickers(request) == ("ASAI3", "EMBR3")


def test_body_chunk_is_not_a_second_headline_or_a_conflicting_event():
    body = replace(hit(extra={"chunk_index": 1}), content="Continuação da notícia")
    instance, _, _ = service([body, hit()], graph())
    result = instance.build("RENT3", as_of=NOW)
    assert len(result["events"]) == 1
    assert result["excluded"]["NON_INITIAL_NEWS_CHUNK"] == 1


def test_existing_hybrid_retriever_preserves_metadata_and_read_only_candidate_count():
    from qdrant_client import QdrantClient
    from b3_agent.knowledge.qdrant_store import QdrantVectorStore
    from b3_agent.knowledge.retrieval import VectorEvidenceRetriever
    from b3_agent.knowledge.embeddings import DeterministicEmbeddingProvider
    from b3_agent.knowledge.evidence import Evidence, EvidenceKind, EvidenceMetadata
    from b3_agent.knowledge.chunking import EvidenceChunker
    client = QdrantClient(":memory:")
    writer = QdrantVectorStore(client=client, collection_name="b3-test", vector_size=8, hybrid=True)
    embeddings = DeterministicEmbeddingProvider(dimensions=8)
    evidence = Evidence("NEWS:1", EvidenceKind.NEWS, "RENT3 publica guidance", "RENT3 publica guidance\n\nTexto da fonte.",
        EvidenceMetadata(document_id=REF, source=REF, published_at=PUB, retrieved_at=PUB,
                         ticker_refs=("RENT3",), topic="news", source_quality="provider"))
    chunks = EvidenceChunker().chunk(evidence)
    writer.upsert(chunks, embeddings.embed(tuple(c.content for c in chunks)))
    reader = QdrantVectorStore(client=client, collection_name="b3-test", vector_size=8, hybrid=True, read_only=True)
    instance = StoredResearchContextService(
        vector_factory=lambda: (VectorEvidenceRetriever(reader, embeddings), lambda: None),
        graph_factory=lambda: (InMemoryKnowledgeGraphStore(), lambda: None))
    result = instance.build("RENT3", as_of=NOW)
    assert result["events"][0]["source_ref"] == REF
    assert result["events"][0]["available_at"] == PUB
    assert instance.build("VALE3", as_of=NOW)["events"] == []
    assert reader.count() == writer.count() == 1
