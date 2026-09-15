from datetime import date

from b3_agent.portfolio.capital_risk import CapitalRiskEngine
from b3_agent.schemas.position import PortfolioContext, Position


def test_short_put_requires_cash_security():
    portfolio = PortfolioContext(
        date(2026, 9, 14),
        (
            Position(
                "put", "ITUBV403", "OPTION", -20,
                strike=40, expiration_date=date(2026, 10, 16),
                option_type="PUT", underlying_ticker="ITUB4", contract_multiplier=100,
            ),
        ),
        cash=90000,
    )
    risk = CapitalRiskEngine().assess(portfolio)
    assert risk.assignment_capital == 80000
    assert risk.cash_after_assignment == 10000
    assert risk.fully_cash_secured is True


def test_insufficient_cash_is_explicit():
    portfolio = PortfolioContext(
        date(2026, 9, 14),
        (
            Position(
                "put", "ITUBV403", "OPTION", -20,
                strike=40, expiration_date=date(2026, 10, 16),
                option_type="PUT", underlying_ticker="ITUB4", contract_multiplier=100,
            ),
        ),
        cash=50000,
    )
    risk = CapitalRiskEngine().assess(portfolio)
    assert risk.cash_after_assignment == -30000
    assert risk.fully_cash_secured is False


def test_uncovered_call_shares_are_detected():
    portfolio = PortfolioContext(
        date(2026, 9, 14),
        (
            Position("stock", "PETR4", "STOCK", 500),
            Position(
                "call", "PETRJ384", "OPTION", -10,
                strike=36, expiration_date=date(2026, 10, 16),
                option_type="CALL", underlying_ticker="PETR4", contract_multiplier=100,
            ),
        ),
    )
    risk = CapitalRiskEngine().assess(portfolio)
    assert risk.uncovered_call_shares == 500
