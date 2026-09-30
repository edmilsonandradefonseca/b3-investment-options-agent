from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import os
import tempfile

from b3_agent.schemas.market import StockMarketData


class MarketDataRepository:
    """Parquet persistence for normalized market observations."""

    COLUMNS = [
        "instrument_id",
        "ticker",
        "observation_timestamp",
        "available_timestamp",
        "source",
        "ingested_at",
        "schema_version",
        "source_record_id",
        "quality_status",
        "quality_flags",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjusted_close",
        "vwap",
        "currency",
    ]

    def __init__(self, root_path: str | Path):
        self.root_path = Path(root_path)

    def write(self, records: list[StockMarketData]) -> Path:
        if not records:
            raise ValueError("records must not be empty")

        ticker = records[0].ticker
        output_dir = self.root_path / f"ticker={ticker}"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / "market.parquet"

        rows = []
        for record in records:
            rows.append(
                {
                    "instrument_id": record.instrument_id,
                    "ticker": record.ticker,
                    "observation_timestamp": record.observation_timestamp,
                    "available_timestamp": record.available_timestamp,
                    "source": record.source,
                    "ingested_at": record.ingested_at,
                    "schema_version": record.schema_version,
                    "source_record_id": record.source_record_id,
                    "quality_status": record.quality_status,
                    "quality_flags": list(record.quality_flags),
                    "open": record.open,
                    "high": record.high,
                    "low": record.low,
                    "close": record.close,
                    "volume": record.volume,
                    "adjusted_close": record.adjusted_close,
                    "vwap": record.vwap,
                    "currency": record.currency,
                }
            )

        table = pa.Table.from_pylist(rows)

        with tempfile.NamedTemporaryFile(dir=output_dir, suffix=".parquet", delete=False) as temp:
            temporary_path = Path(temp.name)
        try:
            pq.write_table(table, temporary_path, compression="zstd")
            os.replace(temporary_path, output_path)
        finally:
            temporary_path.unlink(missing_ok=True)

        return output_path

    def read(self, ticker: str) -> list[StockMarketData]:
        output_path = self.root_path / f"ticker={ticker.upper()}" / "market.parquet"

        if not output_path.exists():
            return []

        # Open the parquet source explicitly so the file descriptor is closed
        # deterministically after every read. Relying on ParquetFile object
        # finalization can accumulate descriptors in long multi-ticker runs.
        with output_path.open("rb") as source:
            table = pq.read_table(source)
        rows = table.to_pylist()

        return [
            StockMarketData(
                instrument_id=row["instrument_id"],
                ticker=row["ticker"],
                observation_timestamp=row["observation_timestamp"],
                available_timestamp=row["available_timestamp"],
                source=row["source"],
                ingested_at=row["ingested_at"],
                schema_version=row["schema_version"],
                source_record_id=row["source_record_id"],
                quality_status=row["quality_status"],
                quality_flags=tuple(row["quality_flags"] or []),
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                adjusted_close=row["adjusted_close"],
                vwap=row["vwap"],
                currency=row["currency"],
            )
            for row in rows
        ]

