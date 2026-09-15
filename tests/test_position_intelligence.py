from datetime import date

from b3_agent.portfolio.position_intelligence import PositionIntelligenceEngine
from b3_agent.schemas.position import Position


def test_assessment_builds_deterministic_role_and_capital_context():
    positions = (
        Position("stock", "ITUB4", "STOCK", 1000, market_value=40000),
        Position("put", "ITUBV403", "OPTION", -20, strike=40, expiration_date=date(2026, 10, 16), option_type="PUT", underlying_ticker="ITUB4", contract_multiplier=100, market_value=-3000),
        Position("call", "ITUBJ438", "OPTION", -10, strike=43.5, expiration_date=date(2026, 10, 16), option_type="CALL", underlying_ticker="ITUB4", contract_multiplier=100, market_value=-1000),
    )
    result = PositionIntelligenceEngine().assess(positions, as_of=date(2026, 9, 14))
    assert len(result) == 3
    assert result[0].side == "LONG"
    assert result[1].assignment_capital == 80000
    assert result[2].deliverable_shares == 1000
    assert all(item.lifecycle.state == "OPEN" for item in result)
