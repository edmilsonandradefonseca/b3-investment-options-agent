from datetime import date

import pytest

from b3_agent.portfolio.context import PortfolioIntelligenceEngine
from b3_agent.schemas.position import PortfolioContext, Position


def test_portfolio_intelligence_composes_assessment_exposure_and_capital_risk():
    portfolio = PortfolioContext(
        as_of=date(2026, 9, 14),
        cash=90000,
        positions=(
            Position("stock", "ITUB4", "STOCK", 1000, market_value=40000),
            Position(
                "put", "ITUBV403", "OPTION", -20,
                strike=40, expiration_date=date(2026, 10, 16),
                option_type="PUT", underlying_ticker="ITUB4", contract_multiplier=100,
                market_value=-3000,
            ),
            Position(
                "call", "ITUBJ438", "OPTION", -10,
                strike=43.5, expiration_date=date(2026, 10, 16),
                option_type="CALL", underlying_ticker="ITUB4", contract_multiplier=100,
                market_value=-1000,
            ),
        ),
    )
    result = PortfolioIntelligenceEngine().build(portfolio)
    assert result.as_of == portfolio.as_of
    assert len(result.assessments) == 3
    assert result.exposures[0].ticker == "ITUB4"
    assert result.exposures[0].assignment_capital == pytest.approx(80000)
    assert result.capital_risk.assignment_capital == pytest.approx(80000)
    assert result.capital_risk.cash_after_assignment == pytest.approx(10000)
    assert result.capital_risk.fully_cash_secured is True
