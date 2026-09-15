from datetime import date

import pytest

from b3_agent.portfolio.capital import CapitalRiskEngine
from b3_agent.schemas.position import PortfolioContext, Position


def test_put_assignment_capital_is_deterministic():
    portfolio = PortfolioContext(
        as_of=date(2026, 9, 14), cash=100000,
        positions=(Position(
            position_id="put", ticker="ITUBV403", instrument_type="OPTION",
            quantity=-20, strike=40, expiration_date=date(2026, 10, 16),
            option_type="PUT", underlying_ticker="ITUB4", contract_multiplier=100,
            market_value=-1000,
        ),),
    )
    risk = CapitalRiskEngine().assess(portfolio)
    assert risk.put_assignment_capital == pytest.approx(80000)
    assert risk.total_capital_at_risk == pytest.approx(180000)
    assert risk.put_assignment_ratio == pytest.approx(0.8)
