from datetime import date, datetime, timezone

from b3_agent.repositories.option_contract import OptionContractRepository
from b3_agent.repositories.option_quote import OptionQuoteRepository
from b3_agent.schemas.option import OptionContract, OptionQuote


def test_option_contract_repository_write_and_read(tmp_path):
    repository = OptionContractRepository(tmp_path / "options")

    record = OptionContract(
        option_id="ITUBI184",
        underlying_id="ITUB4",
        underlying_ticker="ITUB4",
        option_ticker="ITUBI184",
        option_type="CALL",
        strike=40.00,
        expiration_date=date(2026, 10, 16),
        exercise_style="AMERICAN",
        contract_multiplier=100.0,
        currency="BRL",
    )

    path = repository.write([record])

    assert path.exists()

    result = repository.read("ITUB4")

    assert len(result) == 1
    assert result[0].option_id == "ITUBI184"
    assert result[0].option_type == "CALL"
    assert result[0].strike == 40.00
    assert result[0].expiration_date == date(2026, 10, 16)


def test_option_quote_repository_write(tmp_path):
    repository = OptionQuoteRepository(tmp_path / "quotes")

    record = OptionQuote(
        instrument_id="ITUBI184",
        ticker="ITUBI184",
        option_id="ITUBI184",
        observation_timestamp=datetime(
            2026, 9, 11, 21, 45, tzinfo=timezone.utc
        ),
        available_timestamp=datetime(
            2026, 9, 13, 22, 16, tzinfo=timezone.utc
        ),
        source="oplab",
        ingested_at=datetime(
            2026, 9, 13, 22, 16, tzinfo=timezone.utc
        ),
        bid=3.10,
        ask=3.20,
        last=3.15,
        mid=3.15,
        volume=1000.0,
        open_interest=None,
        implied_volatility=None,
        delta=None,
        gamma=None,
        theta=None,
        vega=None,
        rho=None,
    )

    path = repository.write([record], "ITUB4")

    assert path.exists()


