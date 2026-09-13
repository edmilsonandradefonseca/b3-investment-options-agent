from datetime import date, datetime

from b3_agent.repositories.instrument import InstrumentRepository
from b3_agent.schemas.instrument import Instrument
from b3_agent.storage.sqlite import SQLiteStore


def make_instrument(name="Itau Unibanco"):
    return Instrument(
        instrument_id="BR_ITUB4",
        ticker="ITUB4",
        name=name,
        asset_type="EQUITY",
        exchange="B3",
        currency="BRL",
        sector="Financials",
        industry="Banks",
        active=True,
        created_at=datetime(2026, 9, 13, 10, 0),
        updated_at=datetime(2026, 9, 13, 10, 0),
    )


def test_instrument_repository_insert_and_read(tmp_path):
    store = SQLiteStore(tmp_path / "b3_agent.db")
    store.initialize()
    repository = InstrumentRepository(store)

    instrument = make_instrument()
    repository.upsert(instrument)

    result = repository.get_by_ticker("ITUB4")

    assert result is not None
    assert result.instrument_id == "BR_ITUB4"
    assert result.ticker == "ITUB4"
    assert result.name == "Itau Unibanco"
    assert result.sector == "Financials"


def test_instrument_repository_get_by_id(tmp_path):
    store = SQLiteStore(tmp_path / "b3_agent.db")
    store.initialize()
    repository = InstrumentRepository(store)

    repository.upsert(make_instrument())

    result = repository.get_by_id("BR_ITUB4")

    assert result is not None
    assert result.ticker == "ITUB4"


def test_instrument_repository_upsert_updates_existing(tmp_path):
    store = SQLiteStore(tmp_path / "b3_agent.db")
    store.initialize()
    repository = InstrumentRepository(store)

    repository.upsert(make_instrument())
    repository.upsert(make_instrument("Itau Unibanco Holding"))

    result = repository.get_by_ticker("ITUB4")

    assert result is not None
    assert result.name == "Itau Unibanco Holding"

