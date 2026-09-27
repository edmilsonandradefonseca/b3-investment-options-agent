from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from b3_agent.schemas.macro import MacroObservation


class MacroDataRepository:
    """Idempotent Parquet persistence for normalized macro observations.

    source_record_id is the immutable identity. Existing observations win on
    duplicate ingestion so the first-seen availability timestamp is preserved
    for point-in-time reconstruction.
    """

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
        "indicator",
        "value",
        "unit",
        "reference_period",
    ]

    def __init__(self, root_path: str | Path):
        self.root_path = Path(root_path)
        self.output_path = self.root_path / "macro.parquet"

    def upsert(self, records: list[MacroObservation]) -> tuple[int, int]:
        if not records:
            return 0, 0

        existing = self.read_all()
        by_id = {
            item.source_record_id: item
            for item in existing
            if item.source_record_id
        }
        anonymous = [
            item for item in existing if not item.source_record_id
        ]

        inserted = 0
        duplicates = 0
        for record in records:
            if record.source_record_id and record.source_record_id in by_id:
                duplicates += 1
                continue
            if record.source_record_id:
                by_id[record.source_record_id] = record
            else:
                anonymous.append(record)
            inserted += 1

        merged = [*by_id.values(), *anonymous]
        merged.sort(
            key=lambda item: (
                item.indicator,
                item.observation_timestamp,
                item.source_record_id or "",
            )
        )
        self._write(merged)
        return inserted, duplicates

    def read_all(self) -> list[MacroObservation]:
        if not self.output_path.exists():
            return []
        rows = pq.ParquetFile(self.output_path).read().to_pylist()
        return [self._from_row(row) for row in rows]

    def latest(self, indicator: str) -> MacroObservation | None:
        normalized = indicator.upper().strip()
        candidates = [
            item for item in self.read_all()
            if item.indicator.upper() == normalized
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.observation_timestamp)

    def _write(self, records: list[MacroObservation]) -> None:
        self.root_path.mkdir(parents=True, exist_ok=True)
        rows = [self._to_row(item) for item in records]
        table = pa.Table.from_pylist(rows)
        temp_path = self.output_path.with_suffix(".parquet.tmp")
        pq.write_table(table, temp_path, compression="zstd")
        temp_path.replace(self.output_path)

    @classmethod
    def _to_row(cls, record: MacroObservation) -> dict[str, object]:
        return {
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
            "indicator": record.indicator,
            "value": record.value,
            "unit": record.unit,
            "reference_period": record.reference_period,
        }

    @staticmethod
    def _from_row(row: dict[str, object]) -> MacroObservation:
        return MacroObservation(
            instrument_id=str(row["instrument_id"]),
            ticker=str(row["ticker"]),
            observation_timestamp=row["observation_timestamp"],
            available_timestamp=row["available_timestamp"],
            source=str(row["source"]),
            ingested_at=row["ingested_at"],
            schema_version=str(row["schema_version"]),
            source_record_id=(
                str(row["source_record_id"])
                if row["source_record_id"] is not None
                else None
            ),
            quality_status=str(row["quality_status"]),
            quality_flags=tuple(row["quality_flags"] or ()),
            indicator=str(row["indicator"]),
            value=float(row["value"]),
            unit=str(row["unit"]),
            reference_period=(
                str(row["reference_period"])
                if row["reference_period"] is not None
                else None
            ),
        )
