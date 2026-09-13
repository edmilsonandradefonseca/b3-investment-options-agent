from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from b3_agent.schemas.option import OptionContract


class OptionContractRepository:
    def __init__(self, root_path: str | Path):
        self.root_path = Path(root_path)

    def write(self, records: list[OptionContract]) -> Path:
        if not records:
            raise ValueError("records must not be empty")

        ticker = records[0].underlying_ticker
        output_dir = self.root_path / f"ticker={ticker}"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / "contracts.parquet"

        rows = [
            {
                "option_id": r.option_id,
                "underlying_id": r.underlying_id,
                "underlying_ticker": r.underlying_ticker,
                "option_ticker": r.option_ticker,
                "option_type": r.option_type,
                "strike": r.strike,
                "expiration_date": r.expiration_date,
                "exercise_style": r.exercise_style,
                "contract_multiplier": r.contract_multiplier,
                "currency": r.currency,
            }
            for r in records
        ]

        pq.write_table(
            pa.Table.from_pylist(rows),
            output_path,
            compression="zstd",
        )

        return output_path

    def read(self, ticker: str) -> list[OptionContract]:
        output_path = (
            self.root_path
            / f"ticker={ticker.upper()}"
            / "contracts.parquet"
        )

        if not output_path.exists():
            return []

        rows = pq.ParquetFile(output_path).read().to_pylist()

        return [
            OptionContract(
                option_id=row["option_id"],
                underlying_id=row["underlying_id"],
                underlying_ticker=row["underlying_ticker"],
                option_ticker=row["option_ticker"],
                option_type=row["option_type"],
                strike=row["strike"],
                expiration_date=row["expiration_date"],
                exercise_style=row["exercise_style"],
                contract_multiplier=row["contract_multiplier"],
                currency=row["currency"],
            )
            for row in rows
        ]
