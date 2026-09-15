from datetime import date

import pytest

from b3_agent.portfolio import PositionIntelligenceEngine
from b3_agent.schemas.position import PortfolioContext, Position


def test_position_intelligence_groups_underlying_and_calculates_put_assignment_capital():
    portfolio = PortfolioContext(
        as_of=date(2026, 9, 14),
        cash=10000.0,
        positions=(
            Position(
                position_id="stock-itub4",
                ticker="ITUB4",
                instrument_type="STOCK",
                quantity=1000,
                average_cost=35.0,
                market_price=40.0,
                market_value=40000.0,
                source_ref="renda-variavel",
            ),
            Position(
                position_id="put-itubv403",
                ticker="ITUBV403",
                instrument_type="OPTION",
                quantity=-20,
                strike=40.0,
                expiration_date=date(2026, 10, 16),
                option_type="PUT",
                underlying_ticker="ITUB4",
                contract_multiplier=100.0,
                market_value=-3000.0,
                source_ref="renda-variavel",
            ),
        ),
    )

    exposure = PositionIntelligenceEngine().build_exposures(portfolio)[0]
    assert exposure.ticker == "ITUB4"
    assert exposure.quantity == 1000
    assert exposure.option_count == 1
    assert exposure.short_option_count == 1
    assert exposure.assignment_capital == pytest.approx(80000.0)
    assert exposure.market_value == pytest.approx(37000.0)
    assert exposure.gross_market_value == pytest.approx(43000.0)
    assert exposure.net_market_value == pytest.approx(37000.0)
    assert exposure.weight == pytest.approx(37000 / 47000)
    assert exposure.call_coverage_ratio is None


def test_covered_call_ratio_uses_deliverable_shares():
    portfolio = PortfolioContext(
        as_of=date(2026, 9, 14),
        positions=(
            Position(
                position_id="stock-petr4",
                ticker="PETR4",
                instrument_type="STOCK",
                quantity=1000,
                market_value=30000.0,
            ),
            Position(
                position_id="call-petrj384",
                ticker="PETRJ384",
                instrument_type="OPTION",
                quantity=-10,
                strike=36.0,
                expiration_date=date(2026, 10, 16),
                option_type="CALL",
                underlying_ticker="PETR4",
                contract_multiplier=100.0,
                market_value=-500.0,
            ),
        ),
    )

    exposure = PositionIntelligenceEngine().build_exposures(portfolio)[0]
    assert exposure.covered_call_contracts == 10
    assert exposure.call_coverage_ratio == pytest.approx(1.0)


def test_position_rejects_incomplete_option_contract():
    with pytest.raises(ValueError, match="require strike"):
        Position(
            position_id="bad",
            ticker="ITUBV403",
            instrument_type="OPTION",
            quantity=-1,
            option_type="PUT",
            underlying_ticker="ITUB4",
        )
