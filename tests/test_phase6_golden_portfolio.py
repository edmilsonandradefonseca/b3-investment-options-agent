from datetime import date

import pytest

from b3_agent.portfolio import PositionIntelligenceEngine
from b3_agent.portfolio.lifecycle import PositionLifecycleEngine
from b3_agent.portfolio.pnl import PnlEngine
from b3_agent.schemas.position import PortfolioContext, Position

AS_OF = date(2026, 9, 14)
EXPIRY = date(2026, 10, 16)


def option(position_id, ticker, qty, strike, option_type, underlying, multiplier=100):
    return Position(
        position_id=position_id,
        ticker=ticker,
        instrument_type="OPTION",
        quantity=qty,
        strike=strike,
        expiration_date=EXPIRY,
        option_type=option_type,
        underlying_ticker=underlying,
        contract_multiplier=multiplier,
    )


def test_golden_long_stock():
    p = Position("stock", "ITUB4", "STOCK", 1000, average_cost=35, market_price=40, market_value=40000)
    assessment = PositionIntelligenceEngine().assess((p,), as_of=AS_OF)[0]
    pnl = PnlEngine().stock_unrealized(position_id="stock", quantity=1000, average_cost=35, market_price=40)
    assert assessment.side == "LONG"
    assert assessment.assignment_capital == 0
    assert pnl.unrealized_pnl == 5000


def test_golden_short_stock():
    p = Position("stock", "ABEV3", "STOCK", -7000, average_cost=16.34, market_price=15.74, market_value=-109410)
    assessment = PositionIntelligenceEngine().assess((p,), as_of=AS_OF)[0]
    pnl = PnlEngine().stock_unrealized(position_id="stock", quantity=-7000, average_cost=16.34, market_price=15.74)
    assert assessment.side == "SHORT"
    assert pnl.unrealized_pnl == pytest.approx(4200)


def test_golden_short_put():
    p = option("put", "ITUBV403", -20, 40, "PUT", "ITUB4")
    assessment = PositionIntelligenceEngine().assess((p,), as_of=AS_OF)[0]
    assert assessment.side == "SHORT"
    assert assessment.assignment_capital == 80000
    assert assessment.deliverable_shares == 0


def test_golden_covered_call():
    stock = Position("stock", "PETR4", "STOCK", 1000, market_value=30000)
    call = option("call", "PETRJ384", -10, 36, "CALL", "PETR4")
    exposure = PositionIntelligenceEngine().build_exposures(
        PortfolioContext(AS_OF, (stock, call))
    )[0]
    assert exposure.covered_call_contracts == 10
    assert exposure.call_coverage_ratio == pytest.approx(1.0)


def test_golden_put_plus_stock():
    stock = Position("stock", "ITUB4", "STOCK", 1000, market_value=40000)
    put = option("put", "ITUBV403", -20, 40, "PUT", "ITUB4")
    exposure = PositionIntelligenceEngine().build_exposures(
        PortfolioContext(AS_OF, (stock, put), cash=10000)
    )[0]
    assert exposure.quantity == 1000
    assert exposure.assignment_capital == 80000
    assert exposure.market_value == 40000


def test_golden_call_plus_stock():
    stock = Position("stock", "PETR4", "STOCK", 1000, market_value=30000)
    call = option("call", "PETRJ384", -10, 36, "CALL", "PETR4")
    assessments = PositionIntelligenceEngine().assess((stock, call), as_of=AS_OF)
    call_assessment = next(x for x in assessments if x.position_id == "call")
    assert call_assessment.deliverable_shares == 1000


def test_golden_put_and_call_same_underlying():
    stock = Position("stock", "ITUB4", "STOCK", 2000, market_value=80000)
    put = option("put", "ITUBV403", -20, 40, "PUT", "ITUB4")
    call = option("call", "ITUBJ438", -10, 43.5, "CALL", "ITUB4")
    exposure = PositionIntelligenceEngine().build_exposures(
        PortfolioContext(AS_OF, (stock, put, call))
    )[0]
    assert exposure.assignment_capital == 80000
    assert exposure.covered_call_contracts == 10
    assert exposure.call_coverage_ratio == pytest.approx(2.0)


def test_golden_lifecycle_roll_and_replace_are_explicit_transitions():
    engine = PositionLifecycleEngine()
    current = engine.open("put", AS_OF)
    current = engine.transition(current, "MONITOR")
    current = engine.transition(current, "RE_EVALUATE")
    current = engine.transition(current, "ROLL", reason="new expiry preferred")
    current = engine.transition(current, "NEW")
    assert current.state == "NEW"
    current = engine.transition(current, "OPEN")
    current = engine.transition(current, "MONITOR")
    current = engine.transition(current, "RE_EVALUATE")
    current = engine.transition(current, "REPLACE", reason="strategy replacement")
    assert current.reason == "strategy replacement"
