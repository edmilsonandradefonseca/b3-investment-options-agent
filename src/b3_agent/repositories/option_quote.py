from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from b3_agent.schemas.option import OptionQuote


class OptionQuoteRepository:
    def __init__(self, root_path: str | Path):
        self.root_path = Path(root_path)

    def write(self, records: list[OptionQuote], underlying_ticker: str) -> Path:
        if not records:
            raise ValueError("records must not be empty")

        output_dir = self.root_path / f"ticker={underlying_ticker.upper()}"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / "quotes.parquet"

        rows = [r.to_dict() for r in records]

        pq.write_table(
            pa.Table.from_pylist(rows),
            output_path,
            compression="zstd",
        )

        return output_path
