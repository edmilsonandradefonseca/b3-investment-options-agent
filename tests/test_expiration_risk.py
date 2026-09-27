from datetime import date

from b3_agent.portfolio.context import PortfolioIntelligenceEngine
from b3_agent.schemas.position import PortfolioContext, Position


def test_portfolio_intelligence_summarizes_option_expiration_risk():
    portfolio = PortfolioContext(
        as_of=date(2026, 9, 27),
        positions=(
            Position("stock", "ITUB4", "STOCK", 2000, market_value=80000),
            Position("put1", "ITUBV400", "OPTION", -1000, strike=40,
                     expiration_date=date(2026, 10, 16), option_type="PUT",
                     underlying_ticker="ITUB4", market_value=-500),
            Position("put2", "ITUBV420", "OPTION", -500, strike=42,
                     expiration_date=date(2026, 10, 16), option_type="PUT",
                     underlying_ticker="ITUB4", market_value=-400),
            Position("call", "ITUBJ450", "OPTION", -1000, strike=45,
                     expiration_date=date(2026, 11, 20), option_type="CALL",
                     underlying_ticker="ITUB4", market_value=-300),
        ),
    )
    result = PortfolioIntelligenceEngine().build(portfolio)
    assert len(result.expiration_risk) == 2
    october = result.expiration_risk[0]
    assert october.expiration_date == date(2026, 10, 16)
    assert october.option_count == 2
    assert october.short_put_count == 2
    assert october.assignment_capital == 61000
    november = result.expiration_risk[1]
    assert november.short_call_count == 1
    assert november.deliverable_shares == 1000
