from datetime import datetime, timezone
from pathlib import Path

from b3_agent.repositories.market_data import MarketDataRepository
from b3_agent.schemas.market import StockMarketData


def make_record():
    return StockMarketData(
        instrument_id="ITUB4",
        ticker="ITUB4",
        observation_timestamp=datetime(2026, 9, 11, 21, 45, tzinfo=timezone.utc),
        available_timestamp=datetime(2026, 9, 13, 22, 16, tzinfo=timezone.utc),
        source="oplab",
        ingested_at=datetime(2026, 9, 13, 22, 16, tzinfo=timezone.utc),
        source_record_id="ITUB4:123456",
        open=42.55,
        high=42.80,
        low=42.22,
        close=42.80,
        volume=17572900.0,
        adjusted_close=None,
        vwap=None,
        currency="BRL",
    )


def test_market_data_repository_write_and_read(tmp_path):
    repository = MarketDataRepository(tmp_path / "market")

    record = make_record()
    path = repository.write([record])

    assert path.exists()

    result = repository.read("ITUB4")

    assert len(result) == 1
    assert result[0].ticker == "ITUB4"
    assert result[0].close == 42.80
    assert result[0].volume == 17572900.0


def test_market_data_repository_preserves_pit_timestamps(tmp_path):
    repository = MarketDataRepository(tmp_path / "market")

    record = make_record()
    repository.write([record])

    result = repository.read("ITUB4")[0]

    assert result.observation_timestamp == record.observation_timestamp
    assert result.available_timestamp == record.available_timestamp
    assert result.ingested_at == record.ingested_at
    assert result.available_timestamp > result.observation_timestamp


def test_market_data_repository_preserves_quality_metadata(tmp_path):
    repository = MarketDataRepository(tmp_path / "market")

    record = make_record()
    repository.write([record])

    result = repository.read("ITUB4")[0]

    assert result.source == "oplab"
    assert result.source_record_id == "ITUB4:123456"
    assert result.schema_version == "1.0"
    assert result.quality_status == "VALID"
    assert result.quality_flags == ()


def test_market_data_repository_repeated_reads_do_not_leak_file_descriptors(tmp_path):
    fd_root = Path("/proc/self/fd")
    if not fd_root.is_dir():
        return

    repository = MarketDataRepository(tmp_path / "market")
    repository.write([make_record()])

    before = len(list(fd_root.iterdir()))
    for _ in range(100):
        result = repository.read("ITUB4")
        assert result[0].ticker == "ITUB4"
    after = len(list(fd_root.iterdir()))

    assert after <= before + 2
