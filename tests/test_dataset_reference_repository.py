from b3_agent.repositories.dataset_reference import DatasetReferenceRepository
from b3_agent.storage.sqlite import SQLiteStore


def test_dataset_reference_upsert_and_get(tmp_path):
    db_path = tmp_path / "test.db"
    store = SQLiteStore(db_path)
    store.initialize()

    repository = DatasetReferenceRepository(store)

    repository.upsert(
        dataset_id="market-data-brapi",
        dataset_name="market_data",
        storage_format="parquet",
        storage_path="/opt/b3-runtime/data/market",
        schema_version="1.0",
        partition_strategy="ticker",
        first_observation="2026-01-01T00:00:00",
        last_observation="2026-09-21T00:00:00",
        created_at="2026-09-21T10:00:00",
        updated_at="2026-09-21T10:00:00",
    )

    row = repository.get_by_id("market-data-brapi")

    assert row is not None
    assert row[0] == "market-data-brapi"
    assert row[1] == "market_data"
    assert row[2] == "parquet"
    assert row[3] == "/opt/b3-runtime/data/market"
    assert row[4] == "1.0"
    assert row[5] == "ticker"


def test_dataset_reference_upsert_updates_existing_record(tmp_path):
    db_path = tmp_path / "test.db"
    store = SQLiteStore(db_path)
    store.initialize()

    repository = DatasetReferenceRepository(store)

    repository.upsert(
        dataset_id="market-data-brapi",
        dataset_name="market_data",
        storage_format="parquet",
        storage_path="/old/path",
        schema_version="1.0",
    )

    repository.upsert(
        dataset_id="market-data-brapi",
        dataset_name="market_data",
        storage_format="parquet",
        storage_path="/new/path",
        schema_version="1.1",
        partition_strategy="ticker",
    )

    row = repository.get_by_id("market-data-brapi")

    assert row[3] == "/new/path"
    assert row[4] == "1.1"
    assert row[5] == "ticker"


def test_dataset_reference_get_by_name(tmp_path):
    db_path = tmp_path / "test.db"
    store = SQLiteStore(db_path)
    store.initialize()

    repository = DatasetReferenceRepository(store)

    repository.upsert(
        dataset_id="market-data-brapi",
        dataset_name="market_data",
        storage_format="parquet",
        storage_path="/opt/b3-runtime/data/market",
        schema_version="1.0",
    )

    row = repository.get_by_name("market_data")

    assert row is not None
    assert row[0] == "market-data-brapi"
