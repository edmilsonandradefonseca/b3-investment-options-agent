from b3_agent.knowledge.graph_schema import (
    EntityType,
    GraphEntity,
    GraphRelation,
    RelationType,
    validate_relation,
)


def test_v4_learning_and_operation_relations_are_valid():
    operation = GraphEntity("OP-1", EntityType.OPERATION, "OP-1")
    outcome = GraphEntity("OUT-1", EntityType.OUTCOME, "OUT-1")
    regime = GraphEntity("REG-1", EntityType.MARKET_REGIME, "REG-1")
    learning = GraphEntity("LRN-1", EntityType.LEARNING, "LRN-1")
    factor = GraphEntity("FACTOR-BRENT", EntityType.FACTOR, "BRENT")
    instrument = GraphEntity("INSTR-PETR4", EntityType.INSTRUMENT, "B3-PETR4")

    validate_relation(operation, GraphRelation("OP-1", RelationType.HAS_OUTCOME, "OUT-1"), outcome)
    validate_relation(operation, GraphRelation("OP-1", RelationType.OCCURRED_IN, "REG-1"), regime)
    validate_relation(learning, GraphRelation("LRN-1", RelationType.VALID_IN, "REG-1"), regime)
    validate_relation(learning, GraphRelation("LRN-1", RelationType.ASSOCIATED_WITH, "FACTOR-BRENT"), factor)
    validate_relation(instrument, GraphRelation("INSTR-PETR4", RelationType.EXPOSED_TO, "FACTOR-BRENT"), factor)
