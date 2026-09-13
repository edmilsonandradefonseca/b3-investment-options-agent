from datetime import date, datetime

from b3_agent.providers import DataProvider


class FakeProvider(DataProvider):
    name = "fake"

    def get_instruments(self, as_of):
        return []

    def get_market_data(self, ticker, start, end):
        return []

    def get_fundamentals(self, ticker, as_of):
        return []

    def get_corporate_actions(self, ticker, start, end):
        return []

    def get_options(self, ticker, as_of):
        return []

    def get_macro(self, indicator, start, end):
        return []


def test_concrete_provider_can_be_instantiated():
    provider = FakeProvider()

    assert provider.name == "fake"
    assert provider.get_instruments(datetime.now()) == []
    assert provider.get_market_data(
        "PETR4",
        date(2026, 1, 1),
        date(2026, 1, 2),
    ) == []
