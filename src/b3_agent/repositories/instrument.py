from datetime import datetime

from b3_agent.schemas.instrument import Instrument
from b3_agent.storage.sqlite import SQLiteStore


class InstrumentRepository:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def upsert(self, instrument: Instrument) -> None:
        with self.store.connect() as connection:
            connection.execute(
                """
                INSERT INTO instruments (
                    instrument_id,
                    ticker,
                    name,
                    asset_type,
                    exchange,
                    currency,
                    underlying_id,
                    sector,
                    industry,
                    active,
                    active_from,
                    active_to,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(instrument_id) DO UPDATE SET
                    ticker = excluded.ticker,
                    name = excluded.name,
                    asset_type = excluded.asset_type,
                    exchange = excluded.exchange,
                    currency = excluded.currency,
                    underlying_id = excluded.underlying_id,
                    sector = excluded.sector,
                    industry = excluded.industry,
                    active = excluded.active,
                    active_from = excluded.active_from,
                    active_to = excluded.active_to,
                    updated_at = excluded.updated_at
                """,
                (
                    instrument.instrument_id,
                    instrument.ticker,
                    instrument.name,
                    instrument.asset_type,
                    instrument.exchange,
                    instrument.currency,
                    instrument.underlying_id,
                    instrument.sector,
                    instrument.industry,
                    int(instrument.active),
                    instrument.active_from.isoformat()
                    if instrument.active_from else None,
                    instrument.active_to.isoformat()
                    if instrument.active_to else None,
                    instrument.created_at.isoformat()
                    if instrument.created_at else None,
                    instrument.updated_at.isoformat()
                    if instrument.updated_at else datetime.now().isoformat(),
                ),
            )

    def get_by_ticker(self, ticker: str) -> Instrument | None:
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT * FROM instruments WHERE ticker = ?",
                (ticker,),
            ).fetchone()

        return self._from_row(row) if row else None

    def get_by_id(self, instrument_id: str) -> Instrument | None:
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT * FROM instruments WHERE instrument_id = ?",
                (instrument_id,),
            ).fetchone()

        return self._from_row(row) if row else None

    @staticmethod
    def _from_row(row) -> Instrument:
        return Instrument(
            instrument_id=row[0],
            ticker=row[1],
            name=row[2],
            asset_type=row[3],
            exchange=row[4],
            currency=row[5],
            underlying_id=row[6],
            sector=row[7],
            industry=row[8],
            active=bool(row[9]),
            active_from=(
                datetime.fromisoformat(row[10]).date()
                if row[10] else None
            ),
            active_to=(
                datetime.fromisoformat(row[11]).date()
                if row[11] else None
            ),
            created_at=(
                datetime.fromisoformat(row[12])
                if row[12] else None
            ),
            updated_at=(
                datetime.fromisoformat(row[13])
                if row[13] else None
            ),
        )
