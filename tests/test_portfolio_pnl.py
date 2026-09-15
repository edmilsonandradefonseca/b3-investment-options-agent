from b3_agent.portfolio.pnl import PnlEngine


def test_stock_long_unrealized_pnl():
    pnl = PnlEngine().stock_unrealized(
        position_id="itub4", quantity=1000, average_cost=35.0, market_price=40.0
    )
    assert pnl.unrealized_pnl == 5000.0
    assert pnl.realized_pnl == 0.0


def test_stock_short_unrealized_pnl():
    pnl = PnlEngine().stock_unrealized(
        position_id="abev3", quantity=-7000, average_cost=16.34, market_price=15.74
    )
    assert pnl.unrealized_pnl == 4200.0


def test_option_premium_and_buyback_are_separate():
    pnl = PnlEngine().option_snapshot(
        position_id="put-itub", premium_received=1800.0, buyback_cost=700.0,
        realized_pnl=200.0, unrealized_pnl=100.0
    )
    assert pnl.premium_received == 1800.0
    assert pnl.buyback_cost == 700.0
    assert pnl.realized_pnl == 200.0
    assert pnl.unrealized_pnl == 100.0
    assert pnl.net_option_pnl == 1400.0
