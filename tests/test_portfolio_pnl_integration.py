import pytest

from b3_agent.portfolio.pnl import PnlEngine


def test_short_option_mark_to_market_uses_signed_quantity_and_multiplier():
    pnl = PnlEngine().option_from_quotes(
        position_id="itubv403", quantity=-2000, opening_price=1.00,
        current_price=0.60, contract_multiplier=1.0, premium_received=2000.0,
    )
    assert pnl.unrealized_pnl == pytest.approx(800.0)
    assert pnl.premium_received == 2000.0
    assert pnl.buyback_cost == 0.0


def test_option_multiplier_is_applied_without_hardcoding():
    pnl = PnlEngine().option_from_quotes(
        position_id="x", quantity=-20, opening_price=2.0,
        current_price=1.5, contract_multiplier=100.0,
    )
    assert pnl.unrealized_pnl == pytest.approx(1000.0)
