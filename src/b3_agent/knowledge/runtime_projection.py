from __future__ import annotations

from datetime import datetime, time, timezone

from b3_agent.knowledge.chunking import EvidenceChunker
from b3_agent.knowledge.embeddings import EmbeddingProvider
from b3_agent.knowledge.evidence import Evidence, EvidenceKind, EvidenceMetadata
from b3_agent.knowledge.graph_schema import EntityType, GraphEntity, GraphRelation, RelationType
from b3_agent.knowledge.graph_store import KnowledgeGraphStore
from b3_agent.knowledge.qdrant_store import QdrantVectorStore
from b3_agent.research_events import ResearchSnapshot
from b3_agent.schemas.position import PortfolioContext


class RuntimeProjectionService:
    """Project canonical runtime data into rebuildable Neo4j/Qdrant views."""

    def __init__(
        self,
        *,
        graph: KnowledgeGraphStore,
        vector_store: QdrantVectorStore,
        embeddings: EmbeddingProvider,
    ) -> None:
        self.graph = graph
        self.vector_store = vector_store
        self.embeddings = embeddings

    def project_portfolio(self, portfolio: PortfolioContext) -> dict[str, int]:
        as_of = datetime.combine(portfolio.as_of, time.max, tzinfo=timezone.utc)
        portfolio_entity = GraphEntity(
            entity_id="PORTFOLIO:BTG",
            entity_type=EntityType.PORTFOLIO,
            name="BTG Portfolio",
            canonical_id="PORTFOLIO:BTG",
            properties={
                "as_of": portfolio.as_of.isoformat(),
                "cash": portfolio.cash,
                "cash_is_known": portfolio.cash_is_known,
                "quality_status": portfolio.quality_status,
            },
            source_ref=portfolio.source_refs[0] if portfolio.source_refs else None,
            provenance="runtime_projection:v1",
            as_of=as_of,
        )

        entities: list[GraphEntity] = [portfolio_entity]
        relations: list[GraphRelation] = []

        for position in portfolio.positions:
            position_entity = GraphEntity(
                entity_id=f"POSITION:{position.position_id}",
                entity_type=EntityType.POSITION,
                name=position.ticker,
                canonical_id=position.position_id,
                properties={
                    "ticker": position.ticker,
                    "instrument_type": position.instrument_type,
                    "quantity": position.quantity,
                    "average_cost": position.average_cost,
                    "market_price": position.market_price,
                    "market_value": position.market_value,
                    "strike": position.strike,
                    "expiration_date": (
                        position.expiration_date.isoformat()
                        if position.expiration_date is not None
                        else None
                    ),
                    "option_type": position.option_type,
                    "underlying_ticker": position.underlying_ticker,
                    "contract_multiplier": position.contract_multiplier,
                },
                source_ref=position.source_ref or None,
                provenance="runtime_projection:v1",
                as_of=as_of,
            )

            if position.instrument_type == "OPTION":
                instrument_type = EntityType.OPTION
            else:
                instrument_type = EntityType.STOCK

            instrument_entity = GraphEntity(
                entity_id=f"INSTR:{position.ticker}",
                entity_type=instrument_type,
                name=position.ticker,
                canonical_id=position.ticker,
                source_ref=position.source_ref or None,
                provenance="runtime_projection:v1",
                as_of=as_of,
            )
            entities.extend((position_entity, instrument_entity))
            relations.extend(
                (
                    GraphRelation(
                        portfolio_entity.entity_id,
                        RelationType.HAS_POSITION,
                        position_entity.entity_id,
                        source_ref=position.source_ref or None,
                        provenance="runtime_projection:v1",
                        as_of=as_of,
                    ),
                    GraphRelation(
                        position_entity.entity_id,
                        RelationType.INSTRUMENT,
                        instrument_entity.entity_id,
                        source_ref=position.source_ref or None,
                        provenance="runtime_projection:v1",
                        as_of=as_of,
                    ),
                )
            )

            if position.instrument_type == "OPTION" and position.underlying_ticker:
                underlying = GraphEntity(
                    entity_id=f"INSTR:{position.underlying_ticker}",
                    entity_type=EntityType.STOCK,
                    name=position.underlying_ticker,
                    canonical_id=position.underlying_ticker,
                    source_ref=position.source_ref or None,
                    provenance="runtime_projection:v1",
                    as_of=as_of,
                )
                entities.append(underlying)
                relations.append(
                    GraphRelation(
                        instrument_entity.entity_id,
                        RelationType.UNDERLYING,
                        underlying.entity_id,
                        source_ref=position.source_ref or None,
                        provenance="runtime_projection:v1",
                        as_of=as_of,
                    )
                )

        self.graph.upsert(_dedupe_entities(entities), _dedupe_relations(relations))
        return {
            "entities": len(_dedupe_entities(entities)),
            "relations": len(_dedupe_relations(relations)),
        }

    def project_research(self, snapshot: ResearchSnapshot) -> dict[str, int]:
        entities: list[GraphEntity] = []
        relations: list[GraphRelation] = []
        evidences: list[Evidence] = []

        for event in snapshot.events:
            instrument = GraphEntity(
                entity_id=f"INSTR:{event.ticker}",
                entity_type=EntityType.INSTRUMENT,
                name=event.ticker,
                canonical_id=event.ticker,
                provenance="runtime_projection:v1",
                as_of=event.available_at,
            )
            event_entity = GraphEntity(
                entity_id=f"EVENT:{event.event_id}",
                entity_type=EntityType.MARKET_EVENT,
                name=event.headline,
                canonical_id=event.event_id,
                properties={
                    "event_type": event.event_type,
                    "summary": event.summary,
                    "source_name": event.source_name,
                    "relevance": event.relevance,
                },
                source_ref=event.source_ref,
                provenance="runtime_projection:v1",
                as_of=event.available_at,
                valid_from=event.published_at,
            )
            entities.extend((instrument, event_entity))
            relations.append(
                GraphRelation(
                    event_entity.entity_id,
                    RelationType.IMPACTS,
                    instrument.entity_id,
                    source_ref=event.source_ref,
                    provenance="runtime_projection:v1",
                    as_of=event.available_at,
                )
            )

            content = event.headline
            if event.summary:
                content = f"{content}\n\n{event.summary}"
            evidences.append(
                Evidence(
                    evidence_id=f"NEWS:{event.event_id}",
                    kind=EvidenceKind.NEWS,
                    title=event.headline,
                    content=content,
                    source_url=event.source_ref if event.source_ref.startswith(("http://", "https://")) else None,
                    metadata=EvidenceMetadata(
                        document_id=event.event_id,
                        source=event.source_ref,
                        published_at=event.published_at,
                        retrieved_at=event.available_at,
                        ticker_refs=(event.ticker,),
                        event_refs=(event.event_id,),
                        topic="news",
                        source_quality="provider",
                        confidence=1.0,
                        valid_from=event.published_at,
                        extra={
                            "event_type": event.event_type,
                            "source_name": event.source_name,
                            "relevance": event.relevance,
                        },
                    ),
                )
            )

        graph_entities = _dedupe_entities(entities)
        graph_relations = _dedupe_relations(relations)
        self.graph.upsert(graph_entities, graph_relations)

        chunks = []
        for evidence in evidences:
            chunks.extend(EvidenceChunker(max_chars=1200).chunk(evidence))
        if chunks:
            vectors = self.embeddings.embed(tuple(chunk.content for chunk in chunks))
            self.vector_store.upsert(tuple(chunks), vectors)

        return {
            "events": len(snapshot.events),
            "graph_entities": len(graph_entities),
            "graph_relations": len(graph_relations),
            "qdrant_chunks": len(chunks),
        }


def _dedupe_entities(items: list[GraphEntity]) -> tuple[GraphEntity, ...]:
    by_id = {item.entity_id: item for item in items}
    return tuple(by_id[key] for key in sorted(by_id))


def _dedupe_relations(items: list[GraphRelation]) -> tuple[GraphRelation, ...]:
    by_key = {
        (item.source_id, item.relation, item.target_id): item
        for item in items
    }
    return tuple(by_key[key] for key in sorted(by_key, key=str))
