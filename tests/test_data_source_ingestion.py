from b3_agent.repositories.data_source import DataSourceRepository
from b3_agent.repositories.ingestion_run import IngestionRunRepository
from b3_agent.storage.sqlite import SQLiteStore


def test_data_source_repository_upsert_and_read(tmp_path):
    store = SQLiteStore(tmp_path / "b3_agent.db")
    store.initialize()
    repository = DataSourceRepository(store)

    repository.upsert(
        source_id="BRAPI",
        name="BRAPI",
        provider_type="MARKET_DATA",
        base_url="https://brapi.dev",
    )

    result = repository.get_by_id("BRAPI")

    assert result is not None
    assert result[0] == "BRAPI"
    assert result[1] == "BRAPI"
    assert result[2] == "MARKET_DATA"


def test_data_source_repository_update(tmp_path):
    store = SQLiteStore(tmp_path / "b3_agent.db")
    store.initialize()
    repository = DataSourceRepository(store)

    repository.upsert(
        source_id="OPLAB",
        name="OPLAB",
        provider_type="OPTIONS",
    )

    repository.upsert(
        source_id="OPLAB",
        name="OPLAB",
        provider_type="MARKET_AND_OPTIONS",
    )

    result = repository.get_by_name("OPLAB")

    assert result is not None
    assert result[2] == "MARKET_AND_OPTIONS"


def test_ingestion_run_create_and_finish(tmp_path):
    store = SQLiteStore(tmp_path / "b3_agent.db")
    store.initialize()

    data_sources = DataSourceRepository(store)
    runs = IngestionRunRepository(store)

    data_sources.upsert(
        source_id="BRAPI",
        name="BRAPI",
        provider_type="MARKET_DATA",
    )

    runs.create(
        run_id="run-001",
        source_id="BRAPI",
        dataset="market",
        started_at="2026-09-13T10:00:00",
    )

    running = runs.get_by_id("run-001")
    assert running is not None
    assert running[5] == "RUNNING"

    runs.finish(
        run_id="run-001",
        status="SUCCESS",
        finished_at="2026-09-13T10:01:00",
        records_read=100,
        records_written=98,
        records_rejected=2,
    )

    finished = runs.get_by_id("run-001")

    assert finished is not None
    assert finished[5] == "SUCCESS"
    assert finished[6] == 100
    assert finished[7] == 98
    assert finished[8] == 2
