from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class EntityType(StrEnum):
    """Canonical entity types for the B3 investment knowledge graph."""
    INSTRUMENT = "instrument"
    COMPANY = "company"
    STOCK = "stock"
    OPTION = "option"
    ETF = "etf"
    INDEX = "index"
    SECTOR = "sector"
    PORTFOLIO = "portfolio"
    POSITION = "position"
    STRATEGY = "strategy"
    INSIGHT = "insight"
    DECISION = "decision"
    MARKET_EVENT = "market_event"
    RISK = "risk"
    SIGNAL = "signal"
    EVIDENCE = "evidence"


class RelationType(StrEnum):
    """Canonical relationship types between graph entities."""
    TICKER = "ticker"
    ISSUED_BY = "issued_by"
    UNDERLYING = "underlying"
    BELONGS_TO = "belongs_to"
    HAS_POSITION = "has_position"
    INSTRUMENT = "instrument"
    USES = "uses"
    ABOUT = "about"
    SUPPORTED_BY = "supported_by"
    BASED_ON = "based_on"
    AFFECTS = "affects"
    IMPACTS = "impacts"
    DERIVED_FROM = "derived_from"
    RELATED_TO = "related_to"
    PRECEDES = "precedes"
    SUPERSEDES = "supersedes"


@dataclass(frozen=True)
class GraphEntity:
    """A canonical graph node shared with Obsidian/RAG identity."""
    entity_id: str
    entity_type: EntityType
    name: str
    canonical_id: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    source_ref: str | None = None
    provenance: str | None = None
    as_of: datetime | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    def __post_init__(self) -> None:
        if not self.entity_id.strip():
            raise ValueError("entity_id must not be empty")
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError("valid_from must not be after valid_to")


@dataclass(frozen=True)
class GraphRelation:
    """A directed, provenance-aware relationship between two graph nodes."""
    source_id: str
    relation: RelationType
    target_id: str
    properties: dict[str, Any] = field(default_factory=dict)
    source_ref: str | None = None
    provenance: str | None = None
    as_of: datetime | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id must not be empty")
        if not self.target_id.strip():
            raise ValueError("target_id must not be empty")
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError("valid_from must not be after valid_to")


@dataclass(frozen=True)
class KnowledgeGraph:
    """Portable schema container independent of any graph database."""
    entities: tuple[GraphEntity, ...] = ()
    relations: tuple[GraphRelation, ...] = ()


ENTITY_RELATION_RULES: dict[RelationType, tuple[set[EntityType], set[EntityType]]] = {
    RelationType.TICKER: ({EntityType.COMPANY, EntityType.STOCK}, {EntityType.INSTRUMENT, EntityType.STOCK}),
    RelationType.ISSUED_BY: ({EntityType.STOCK, EntityType.OPTION, EntityType.ETF}, {EntityType.COMPANY}),
    RelationType.UNDERLYING: ({EntityType.OPTION}, {EntityType.STOCK, EntityType.ETF, EntityType.INDEX}),
    RelationType.BELONGS_TO: ({EntityType.STOCK, EntityType.COMPANY, EntityType.ETF}, {EntityType.SECTOR}),
    RelationType.HAS_POSITION: ({EntityType.PORTFOLIO}, {EntityType.POSITION}),
    RelationType.INSTRUMENT: ({EntityType.POSITION, EntityType.OPTION, EntityType.STRATEGY}, {EntityType.INSTRUMENT, EntityType.STOCK, EntityType.OPTION}),
    RelationType.USES: ({EntityType.STRATEGY}, {EntityType.OPTION, EntityType.INSTRUMENT}),
    RelationType.ABOUT: ({EntityType.INSIGHT, EntityType.DECISION, EntityType.RISK, EntityType.SIGNAL}, {EntityType.INSTRUMENT, EntityType.STOCK, EntityType.COMPANY, EntityType.PORTFOLIO, EntityType.OPTION}),
    RelationType.SUPPORTED_BY: ({EntityType.INSIGHT, EntityType.DECISION}, {EntityType.EVIDENCE, EntityType.INSIGHT}),
    RelationType.BASED_ON: ({EntityType.DECISION}, {EntityType.INSIGHT, EntityType.SIGNAL, EntityType.EVIDENCE}),
    RelationType.AFFECTS: ({EntityType.RISK}, {EntityType.POSITION, EntityType.INSTRUMENT, EntityType.PORTFOLIO}),
    RelationType.IMPACTS: ({EntityType.MARKET_EVENT}, {EntityType.INSTRUMENT, EntityType.COMPANY, EntityType.SECTOR}),
    RelationType.DERIVED_FROM: ({EntityType.INSIGHT, EntityType.SIGNAL}, {EntityType.EVIDENCE, EntityType.INSIGHT}),
    RelationType.RELATED_TO: (set(EntityType), set(EntityType)),
    RelationType.PRECEDES: ({EntityType.INSIGHT, EntityType.DECISION, EntityType.MARKET_EVENT}, {EntityType.INSIGHT, EntityType.DECISION, EntityType.MARKET_EVENT}),
    RelationType.SUPERSEDES: ({EntityType.INSIGHT, EntityType.DECISION}, {EntityType.INSIGHT, EntityType.DECISION}),
}


def validate_relation(source: GraphEntity, relation: GraphRelation, target: GraphEntity) -> None:
    """Validate that a relation connects compatible canonical entity types."""
    if relation.source_id != source.entity_id or relation.target_id != target.entity_id:
        raise ValueError("relation endpoints do not match supplied entities")
    allowed_sources, allowed_targets = ENTITY_RELATION_RULES[relation.relation]
    if source.entity_type not in allowed_sources:
        raise ValueError(f"invalid source type for {relation.relation}: {source.entity_type}")
    if target.entity_type not in allowed_targets:
        raise ValueError(f"invalid target type for {relation.relation}: {target.entity_type}")
