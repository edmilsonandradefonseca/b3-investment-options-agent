from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path

from b3_agent.knowledge.graph_schema import (
    EntityType,
    GraphEntity,
    GraphRelation,
    RelationType,
)
from b3_agent.knowledge.graph_store import KnowledgeGraphStore
from b3_agent.knowledge.learning_semantic import LearningSemanticIndex
from b3_agent.schemas.learning import EvidenceDirection, Learning
from b3_agent.schemas.market_regime import MarketRegime
from b3_agent.schemas.operation import Operation
from b3_agent.schemas.outcome import Outcome


@dataclass(frozen=True)
class ProjectionStatus:
    canonical_id: str
    canonical_version: str
    target: str
    status: str
    projected_at: datetime
    error: str | None = None


class SQLiteProjectionLedger:
    """Track rebuildable memory projection status without making projections canonical."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_projection_status (
                    canonical_id TEXT NOT NULL,
                    canonical_version TEXT NOT NULL,
                    target TEXT NOT NULL,
                    status TEXT NOT NULL,
                    projected_at TEXT NOT NULL,
                    error TEXT,
                    PRIMARY KEY (canonical_id, canonical_version, target)
                )
                """
            )
            connection.commit()

    def record(
        self,
        *,
        canonical_id: str,
        canonical_version: str,
        target: str,
        status: str,
        error: str | None = None,
        projected_at: datetime | None = None,
    ) -> None:
        when = projected_at or datetime.now(timezone.utc)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO memory_projection_status (
                    canonical_id, canonical_version, target,
                    status, projected_at, error
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(canonical_id, canonical_version, target)
                DO UPDATE SET
                    status=excluded.status,
                    projected_at=excluded.projected_at,
                    error=excluded.error
                """,
                (
                    canonical_id,
                    canonical_version,
                    target,
                    status,
                    when.isoformat(),
                    error,
                ),
            )
            connection.commit()

    def get(
        self,
        canonical_id: str,
        canonical_version: str,
    ) -> tuple[ProjectionStatus, ...]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT canonical_id, canonical_version, target,
                       status, projected_at, error
                FROM memory_projection_status
                WHERE canonical_id = ? AND canonical_version = ?
                ORDER BY target
                """,
                (canonical_id, canonical_version),
            ).fetchall()
        return tuple(
            ProjectionStatus(
                canonical_id=row["canonical_id"],
                canonical_version=row["canonical_version"],
                target=row["target"],
                status=row["status"],
                projected_at=datetime.fromisoformat(row["projected_at"]),
                error=row["error"],
            )
            for row in rows
        )


class MemoryProjectionBridge:
    """Project canonical V4 domain state into Qdrant and Neo4j.

    The bridge assumes canonical structured state has already been committed.
    Projection failures are recorded as degraded states and are retryable.
    """

    def __init__(
        self,
        *,
        graph: KnowledgeGraphStore,
        ledger: SQLiteProjectionLedger,
        semantic: LearningSemanticIndex | None = None,
    ) -> None:
        self.graph = graph
        self.ledger = ledger
        self.semantic = semantic

    def project_operation(
        self,
        *,
        operation: Operation,
        outcome: Outcome | None = None,
        regime: MarketRegime | None = None,
    ) -> None:
        entities, relations = _operation_graph(operation, outcome=outcome, regime=regime)
        self._project_graph(operation.operation_id, operation.schema_version, entities, relations)

    def project_learning(self, learning: Learning) -> None:
        entities, relations = _learning_graph(learning)
        self._project_graph(learning.learning_id, learning.schema_version, entities, relations)

        if self.semantic is None:
            return

        try:
            self.semantic.upsert((learning,))
        except Exception as exc:
            self.ledger.record(
                canonical_id=learning.learning_id,
                canonical_version=learning.schema_version,
                target="qdrant",
                status="FAILED",
                error=str(exc),
            )
            raise
        else:
            self.ledger.record(
                canonical_id=learning.learning_id,
                canonical_version=learning.schema_version,
                target="qdrant",
                status="OK",
            )

    def _project_graph(
        self,
        canonical_id: str,
        canonical_version: str,
        entities: tuple[GraphEntity, ...],
        relations: tuple[GraphRelation, ...],
    ) -> None:
        try:
            self.graph.upsert(entities, relations)
        except Exception as exc:
            self.ledger.record(
                canonical_id=canonical_id,
                canonical_version=canonical_version,
                target="neo4j",
                status="FAILED",
                error=str(exc),
            )
            raise
        else:
            self.ledger.record(
                canonical_id=canonical_id,
                canonical_version=canonical_version,
                target="neo4j",
                status="OK",
            )


def _operation_graph(
    operation: Operation,
    *,
    outcome: Outcome | None,
    regime: MarketRegime | None,
) -> tuple[tuple[GraphEntity, ...], tuple[GraphRelation, ...]]:
    instrument = GraphEntity(
        entity_id=f"INSTR-{operation.underlying_id}",
        entity_type=EntityType.INSTRUMENT,
        name=operation.underlying_id,
        canonical_id=operation.underlying_id,
        provenance="memory_projection_bridge:v1",
    )
    strategy = GraphEntity(
        entity_id=f"STRAT-{operation.strategy_type}",
        entity_type=EntityType.STRATEGY,
        name=operation.strategy_type,
        canonical_id=operation.strategy_type,
        provenance="memory_projection_bridge:v1",
    )
    op = GraphEntity(
        entity_id=operation.operation_id,
        entity_type=EntityType.OPERATION,
        name=operation.operation_id,
        canonical_id=operation.operation_id,
        properties={
            "status": operation.status.value,
            "direction": operation.direction.value,
            "quantity": operation.quantity,
            "capital_committed": operation.capital_committed,
            "schema_version": operation.schema_version,
        },
        provenance=operation.provenance or "memory_projection_bridge:v1",
        as_of=operation.opened_at,
        valid_from=operation.opened_at,
        valid_to=operation.closed_at,
    )
    entities: list[GraphEntity] = [instrument, strategy, op]
    relations: list[GraphRelation] = [
        GraphRelation(
            source_id=op.entity_id,
            relation=RelationType.ABOUT,
            target_id=instrument.entity_id,
            provenance="memory_projection_bridge:v1",
            as_of=operation.opened_at,
        ),
        GraphRelation(
            source_id=op.entity_id,
            relation=RelationType.USES,
            target_id=strategy.entity_id,
            provenance="memory_projection_bridge:v1",
            as_of=operation.opened_at,
        ),
    ]

    if outcome is not None:
        outcome_entity = GraphEntity(
            entity_id=outcome.outcome_id,
            entity_type=EntityType.OUTCOME,
            name=outcome.outcome_id,
            canonical_id=outcome.outcome_id,
            properties={
                "status": outcome.status.value,
                "realized_pnl": outcome.realized_pnl,
                "realized_return": outcome.realized_return,
                "holding_period_days": outcome.holding_period_days,
                "schema_version": outcome.schema_version,
            },
            provenance=outcome.provenance or "memory_projection_bridge:v1",
            as_of=outcome.finalized_at,
        )
        entities.append(outcome_entity)
        relations.append(
            GraphRelation(
                op.entity_id,
                RelationType.HAS_OUTCOME,
                outcome_entity.entity_id,
                provenance="memory_projection_bridge:v1",
                as_of=outcome.finalized_at,
            )
        )

    if regime is not None:
        regime_entity = _regime_entity(regime)
        entities.append(regime_entity)
        relations.append(
            GraphRelation(
                op.entity_id,
                RelationType.OCCURRED_IN,
                regime_entity.entity_id,
                provenance="memory_projection_bridge:v1",
                as_of=operation.opened_at,
            )
        )

    return tuple(entities), tuple(relations)


def _learning_graph(
    learning: Learning,
) -> tuple[tuple[GraphEntity, ...], tuple[GraphRelation, ...]]:
    learning_entity = GraphEntity(
        entity_id=learning.learning_id,
        entity_type=EntityType.LEARNING,
        name=learning.learning_id,
        canonical_id=learning.learning_id,
        properties={
            "statement": learning.statement,
            "status": learning.status.value,
            "scope": learning.learning_scope.value,
            "sample_size": learning.sample_size,
            "win_rate": learning.win_rate,
            "expected_return": learning.expected_return,
            "confidence": learning.confidence,
            "statistical_method": learning.statistical_method,
            "schema_version": learning.schema_version,
        },
        provenance=learning.provenance or "memory_projection_bridge:v1",
        as_of=learning.last_updated_at,
        valid_from=learning.valid_from,
        valid_to=learning.valid_to,
    )

    entities: list[GraphEntity] = [learning_entity]
    relations: list[GraphRelation] = []

    for subject_id in learning.subject_ids:
        instrument = GraphEntity(
            entity_id=f"INSTR-{subject_id}",
            entity_type=EntityType.INSTRUMENT,
            name=subject_id,
            canonical_id=subject_id,
            provenance="memory_projection_bridge:v1",
        )
        entities.append(instrument)
        relations.append(
            GraphRelation(
                learning_entity.entity_id,
                RelationType.ABOUT,
                instrument.entity_id,
                provenance="memory_projection_bridge:v1",
                as_of=learning.last_updated_at,
            )
        )

    for regime_id in learning.regime_ids:
        regime = GraphEntity(
            entity_id=regime_id,
            entity_type=EntityType.MARKET_REGIME,
            name=regime_id,
            canonical_id=regime_id,
            provenance="memory_projection_bridge:v1",
        )
        entities.append(regime)
        relations.append(
            GraphRelation(
                learning_entity.entity_id,
                RelationType.VALID_IN,
                regime.entity_id,
                provenance="memory_projection_bridge:v1",
                as_of=learning.last_updated_at,
            )
        )

    for evidence in learning.evidence_links:
        if evidence.operation_id is None:
            continue
        operation = GraphEntity(
            entity_id=evidence.operation_id,
            entity_type=EntityType.OPERATION,
            name=evidence.operation_id,
            canonical_id=evidence.operation_id,
            provenance="memory_projection_bridge:v1",
        )
        entities.append(operation)
        relation_type = (
            RelationType.SUPPORTED_BY
            if evidence.direction == EvidenceDirection.SUPPORTS
            else RelationType.CONTRADICTED_BY
        )
        relations.append(
            GraphRelation(
                learning_entity.entity_id,
                relation_type,
                operation.entity_id,
                source_ref=evidence.source_ref,
                provenance="memory_projection_bridge:v1",
                as_of=evidence.observed_at,
            )
        )

    for old_id in learning.supersedes:
        old = GraphEntity(
            entity_id=old_id,
            entity_type=EntityType.LEARNING,
            name=old_id,
            canonical_id=old_id,
            provenance="memory_projection_bridge:v1",
        )
        entities.append(old)
        relations.append(
            GraphRelation(
                learning_entity.entity_id,
                RelationType.SUPERSEDES,
                old.entity_id,
                provenance="memory_projection_bridge:v1",
                as_of=learning.last_updated_at,
            )
        )

    return _dedupe_entities(entities), tuple(relations)


def _regime_entity(regime: MarketRegime) -> GraphEntity:
    return GraphEntity(
        entity_id=regime.regime_id,
        entity_type=EntityType.MARKET_REGIME,
        name=regime.regime_id,
        canonical_id=regime.regime_id,
        properties={
            "classifier_version": regime.classifier_version,
            "confidence": regime.confidence,
            "dimensions": {
                item.name.value: item.label for item in regime.dimensions
            },
            "schema_version": regime.schema_version,
        },
        provenance=regime.provenance or "memory_projection_bridge:v1",
        as_of=regime.as_of,
        valid_from=regime.valid_from,
        valid_to=regime.valid_to,
    )


def _dedupe_entities(entities: list[GraphEntity]) -> tuple[GraphEntity, ...]:
    by_id: dict[str, GraphEntity] = {}
    for entity in entities:
        by_id[entity.entity_id] = entity
    return tuple(by_id[key] for key in sorted(by_id))
