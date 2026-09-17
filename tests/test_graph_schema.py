from datetime import datetime, timezone

import pytest

from b3_agent.knowledge.graph_schema import (
    EntityType,
    GraphEntity,
    GraphRelation,
    RelationType,
    validate_relation,
)


def entity(entity_id: str, entity_type: EntityType, name: str) -> GraphEntity:
    return GraphEntity(
        entity_id=entity_id,
        entity_type=entity_type,
        name=name,
        canonical_id=name,
        source_ref="obsidian:example.md",
        provenance="test",
        as_of=datetime(2026, 9, 16, tzinfo=timezone.utc),
    )


def test_option_underlying_relation_is_valid() -> None:
    option = entity("OPT-PETRI32", EntityType.OPTION, "PETRI32")
    stock = entity("STK-PETR4", EntityType.STOCK, "PETR4")
    relation = GraphRelation(option.entity_id, RelationType.UNDERLYING, stock.entity_id)

    validate_relation(option, relation, stock)


def test_invalid_relation_type_is_rejected() -> None:
    portfolio = entity("PORT-1", EntityType.PORTFOLIO, "Portfolio")
    stock = entity("STK-PETR4", EntityType.STOCK, "PETR4")
    relation = GraphRelation(portfolio.entity_id, RelationType.UNDERLYING, stock.entity_id)

    with pytest.raises(ValueError, match="invalid source type"):
        validate_relation(portfolio, relation, stock)


def test_temporal_interval_is_validated() -> None:
    with pytest.raises(ValueError, match="valid_from"):
        GraphEntity(
            entity_id="E1",
            entity_type=EntityType.STOCK,
            name="PETR4",
            valid_from=datetime(2026, 9, 17, tzinfo=timezone.utc),
            valid_to=datetime(2026, 9, 16, tzinfo=timezone.utc),
        )


def test_shared_identity_fields_are_available() -> None:
    stock = entity("STK-PETR4", EntityType.STOCK, "PETR4")

    assert stock.canonical_id == "PETR4"
    assert stock.source_ref == "obsidian:example.md"
    assert stock.provenance == "test"
    assert stock.as_of is not None
