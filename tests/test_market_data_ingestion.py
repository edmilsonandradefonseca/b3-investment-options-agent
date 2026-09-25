from datetime import date, datetime, timezone

from b3_agent.repositories.data_source import DataSourceRepository
from b3_agent.repositories.dataset_reference import DatasetReferenceRepository
from b3_agent.repositories.ingestion_run import IngestionRunRepository
from b3_agent.repositories.market_data import MarketDataRepository
from b3_agent.schemas.market import StockMarketData
from b3_agent.storage.sqlite import SQLiteStore


class FakeMarketDataProvider:
    name = "fake"

    def get_market_data(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> list[StockMarketData]:
        timestamp = datetime(2026, 9, 18, 21, 0, tzinfo=timezone.utc)

        return [
            StockMarketData(
                instrument_id=ticker,
                ticker=ticker,
                observation_timestamp=timestamp,
                available_timestamp=timestamp,
                source=self.name,
                ingested_at=timestamp,
                source_record_id=f"{ticker}:1",
                open=100.0,
                high=105.0,
                low=99.0,
                close=103.0,
                volume=1000.0,
                currency="BRL",
            )
        ]


def test_market_data_ingestion_persists_data_and_metadata(tmp_path):
    db_path = tmp_path / "b3.db"
    market_root = tmp_path / "market"

    store = SQLiteStore(db_path)
    store.initialize()

    data_sources = DataSourceRepository(store)
    ingestion_runs = IngestionRunRepository(store)
    dataset_references = DatasetReferenceRepository(store)
    market_data = MarketDataRepository(market_root)

    data_sources.upsert(
        source_id="fake",
        name="fake",
        provider_type="market_data",
    )

    provider = FakeMarketDataProvider()

    from b3_agent.services.market_data_ingestion import MarketDataIngestionService

    service = MarketDataIngestionService(
        provider=provider,
        market_data_repository=market_data,
        data_source_repository=data_sources,
        ingestion_run_repository=ingestion_runs,
        dataset_reference_repository=dataset_references,
    )

    result = service.ingest(
        ticker="ITUB4",
        start=date(2026, 9, 18),
        end=date(2026, 9, 18),
    )

    assert result.records_read == 1
    assert result.records_written == 1
    assert result.records_rejected == 0

    stored = market_data.read("ITUB4")
    assert len(stored) == 1
    assert stored[0].close == 103.0

    dataset = dataset_references.get_by_name("market_data")
    assert dataset is not None

    run = ingestion_runs.get_by_id(result.run_id)
    assert run is not None
    assert run[5] == "SUCCESS"
    assert run[6] == 1
    assert run[7] == 1
    assert run[8] == 0


def test_market_data_ingestion_rejects_empty_provider_result(tmp_path):
    db_path = tmp_path / "b3.db"
    market_root = tmp_path / "market"

    store = SQLiteStore(db_path)
    store.initialize()

    data_sources = DataSourceRepository(store)
    ingestion_runs = IngestionRunRepository(store)
    dataset_references = DatasetReferenceRepository(store)
    market_data = MarketDataRepository(market_root)

    data_sources.upsert(
        source_id="fake",
        name="fake",
        provider_type="market_data",
    )

    class EmptyProvider(FakeMarketDataProvider):
        def get_market_data(self, ticker, start, end):
            return []

    from b3_agent.services.market_data_ingestion import MarketDataIngestionService

    service = MarketDataIngestionService(
        provider=EmptyProvider(),
        market_data_repository=market_data,
        data_source_repository=data_sources,
        ingestion_run_repository=ingestion_runs,
        dataset_reference_repository=dataset_references,
    )

    try:
        service.ingest(
            ticker="ITUB4",
            start=date(2026, 9, 18),
            end=date(2026, 9, 18),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for empty provider result")

    with store.connect() as connection:
        row = connection.execute(
            "SELECT run_id FROM ingestion_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()

    assert row is not None

    run = ingestion_runs.get_by_id(row[0])

    assert run is not None
    assert run[5] == "FAILED"
    assert run[6] == 0
    assert run[7] == 0
    assert run[8] == 0
