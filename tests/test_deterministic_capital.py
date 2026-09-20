from datetime import date

from b3_agent.orchestration.deterministic import build_opportunity_set
from b3_agent.schemas.position import PortfolioContext


class RecordingPipeline:
    def __init__(self):
        self.available_capital = None

    def build_from_inputs(self, **kwargs):
        self.available_capital = kwargs["available_capital"]
        return kwargs["available_capital"]


def test_build_opportunity_set_derives_available_capital_from_portfolio():
    pipeline = RecordingPipeline()
    portfolio = PortfolioContext(
        as_of=date(2026, 9, 18),
        cash=80_000,
        positions=(),
    )

    result = build_opportunity_set(
        as_of=date(2026, 9, 18),
        pipeline=pipeline,
        portfolio_context=portfolio,
    )

    assert result == 80_000
    assert pipeline.available_capital == 80_000


def test_build_opportunity_set_explicit_capital_overrides_portfolio_cash():
    pipeline = RecordingPipeline()
    portfolio = PortfolioContext(
        as_of=date(2026, 9, 18),
        cash=80_000,
        positions=(),
    )

    result = build_opportunity_set(
        as_of=date(2026, 9, 18),
        pipeline=pipeline,
        portfolio_context=portfolio,
        available_capital=20_000,
    )

    assert result == 20_000
    assert pipeline.available_capital == 20_000


def test_build_opportunity_set_without_portfolio_keeps_capital_unset():
    pipeline = RecordingPipeline()

    result = build_opportunity_set(
        as_of=date(2026, 9, 18),
        pipeline=pipeline,
    )

    assert result is None
    assert pipeline.available_capital is None
