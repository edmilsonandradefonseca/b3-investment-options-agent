from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
import re
import sqlite3
from typing import Any

from b3_agent.config import settings
from b3_agent.providers.cvm_open_data import (
    CvmOpenDataIssuerRecord,
    CvmOpenDataProvider,
    CvmOpenDataSecurityRecord,
)


@dataclass(frozen=True)
class Issuer:
    issuer_id: str
    cvm_code: str | None
    cnpj: str | None
    legal_name: str
    trading_name: str | None
    registration_status: str | None


@dataclass(frozen=True)
class Security:
    instrument_id: str
    ticker: str
    issuer_id: str
    asset_type: str | None
    description: str | None
    market: str | None
    exchange: str | None
    trading_start: date | None
    trading_end: date | None
    reference_date: date | None

    def is_active(self, *, as_of: date | None = None) -> bool:
        target = as_of or date.today()
        if self.trading_start is not None and self.trading_start > target:
            return False
        return self.trading_end is None or self.trading_end >= target


class IssuerRegistry:
    """Canonical deterministic mapping: CVM issuer identity <-> B3 securities.

    Source authority is CVM Open Data:
    - CAD: CVM code, CNPJ and issuer names;
    - FCA valor_mobiliario: issuer CNPJ and exchange trading code.

    The registry is structured truth. It does not infer tickers from names and
    never asks an LLM to resolve issuer identity.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(
            path or settings.data_dir / "structured" / "issuer_registry.sqlite3"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS issuers (
                    issuer_id TEXT PRIMARY KEY,
                    cvm_code TEXT,
                    cnpj TEXT,
                    legal_name TEXT NOT NULL,
                    trading_name TEXT,
                    registration_status TEXT,
                    source TEXT NOT NULL,
                    source_retrieved_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_issuers_cvm_code
                    ON issuers(cvm_code);
                CREATE INDEX IF NOT EXISTS idx_issuers_cnpj
                    ON issuers(cnpj);

                CREATE TABLE IF NOT EXISTS securities (
                    instrument_id TEXT PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    issuer_id TEXT NOT NULL,
                    asset_type TEXT,
                    description TEXT,
                    market TEXT,
                    exchange_name TEXT,
                    trading_start TEXT,
                    trading_end TEXT,
                    reference_date TEXT,
                    source TEXT NOT NULL,
                    source_retrieved_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (issuer_id) REFERENCES issuers(issuer_id)
                );

                CREATE INDEX IF NOT EXISTS idx_securities_ticker
                    ON securities(ticker);
                CREATE INDEX IF NOT EXISTS idx_securities_issuer
                    ON securities(issuer_id);

                CREATE TABLE IF NOT EXISTS issuer_registry_sync_runs (
                    sync_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    fca_year INTEGER NOT NULL,
                    issuer_count INTEGER NOT NULL,
                    security_count INTEGER NOT NULL,
                    active_security_count INTEGER NOT NULL,
                    unmatched_security_count INTEGER NOT NULL,
                    skipped_issuer_count INTEGER NOT NULL
                );
                """
            )

    def sync_from_cvm(
        self,
        *,
        provider: CvmOpenDataProvider | None = None,
        year: int | None = None,
        as_of: date | None = None,
    ) -> dict[str, Any]:
        provider = provider or CvmOpenDataProvider()
        target_date = as_of or datetime.now(timezone.utc).date()
        target_year = year or target_date.year
        started_at = datetime.now(timezone.utc)

        issuer_result = provider.fetch_issuers()
        security_result = provider.fetch_fca_securities(target_year)

        issuer_by_cnpj: dict[str, CvmOpenDataIssuerRecord] = {}
        skipped_issuers = 0
        for record in issuer_result.issuers:
            issuer_id = _issuer_id(record)
            if issuer_id is None:
                skipped_issuers += 1
                continue
            if record.cnpj:
                current = issuer_by_cnpj.get(record.cnpj)
                if current is None or _issuer_rank(record) > _issuer_rank(current):
                    issuer_by_cnpj[record.cnpj] = record

        latest_securities: dict[tuple[str, str], CvmOpenDataSecurityRecord] = {}
        for record in security_result.securities:
            if not record.cnpj:
                continue
            key = (record.cnpj, record.ticker)
            current = latest_securities.get(key)
            if current is None or _security_rank(record) > _security_rank(current):
                latest_securities[key] = record

        now = datetime.now(timezone.utc)
        issuer_count = 0
        security_count = 0
        active_security_count = 0
        unmatched_security_count = 0

        with self._connect() as conn:
            for record in issuer_result.issuers:
                issuer_id = _issuer_id(record)
                if issuer_id is None:
                    continue
                conn.execute(
                    """
                    INSERT INTO issuers (
                        issuer_id, cvm_code, cnpj, legal_name, trading_name,
                        registration_status, source, source_retrieved_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(issuer_id) DO UPDATE SET
                        cvm_code = excluded.cvm_code,
                        cnpj = excluded.cnpj,
                        legal_name = excluded.legal_name,
                        trading_name = excluded.trading_name,
                        registration_status = excluded.registration_status,
                        source = excluded.source,
                        source_retrieved_at = excluded.source_retrieved_at,
                        updated_at = excluded.updated_at
                    """,
                    (
                        issuer_id,
                        record.cvm_code,
                        record.cnpj,
                        record.legal_name,
                        record.trading_name,
                        record.registration_status,
                        "CVM_CAD_OPEN_DATA",
                        record.retrieved_at.isoformat(),
                        now.isoformat(),
                    ),
                )
                issuer_count += 1

            for record in latest_securities.values():
                issuer_record = issuer_by_cnpj.get(record.cnpj or "")
                if issuer_record is None:
                    unmatched_security_count += 1
                    continue
                issuer_id = _issuer_id(issuer_record)
                if issuer_id is None:
                    unmatched_security_count += 1
                    continue

                instrument_id = f"cvm-security:{issuer_id}:{record.ticker}"
                conn.execute(
                    """
                    INSERT INTO securities (
                        instrument_id, ticker, issuer_id, asset_type, description,
                        market, exchange_name, trading_start, trading_end,
                        reference_date, source, source_retrieved_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(instrument_id) DO UPDATE SET
                        ticker = excluded.ticker,
                        issuer_id = excluded.issuer_id,
                        asset_type = excluded.asset_type,
                        description = excluded.description,
                        market = excluded.market,
                        exchange_name = excluded.exchange_name,
                        trading_start = excluded.trading_start,
                        trading_end = excluded.trading_end,
                        reference_date = excluded.reference_date,
                        source = excluded.source,
                        source_retrieved_at = excluded.source_retrieved_at,
                        updated_at = excluded.updated_at
                    """,
                    (
                        instrument_id,
                        record.ticker,
                        issuer_id,
                        record.security_type,
                        record.security_description,
                        record.market,
                        record.exchange,
                        _date_text(record.trading_start),
                        _date_text(record.trading_end),
                        _date_text(record.reference_date),
                        "CVM_FCA_OPEN_DATA",
                        record.retrieved_at.isoformat(),
                        now.isoformat(),
                    ),
                )
                security_count += 1
                if record.is_active(as_of=target_date):
                    active_security_count += 1

            completed_at = datetime.now(timezone.utc)
            sync_id = (
                f"cvm-open-data:{target_year}:"
                f"{completed_at.strftime('%Y%m%dT%H%M%S%fZ')}"
            )
            conn.execute(
                """
                INSERT INTO issuer_registry_sync_runs (
                    sync_id, started_at, completed_at, fca_year,
                    issuer_count, security_count, active_security_count,
                    unmatched_security_count, skipped_issuer_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sync_id,
                    started_at.isoformat(),
                    completed_at.isoformat(),
                    target_year,
                    issuer_count,
                    security_count,
                    active_security_count,
                    unmatched_security_count,
                    skipped_issuers,
                ),
            )

        return {
            "sync_id": sync_id,
            "source": "CVM_OPEN_DATA",
            "fca_year": target_year,
            "issuer_count": issuer_count,
            "security_count": security_count,
            "active_security_count": active_security_count,
            "unmatched_security_count": unmatched_security_count,
            "skipped_issuer_count": skipped_issuers,
            "issuer_source_url": issuer_result.source_url,
            "security_source_url": security_result.source_url,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }

    def resolve_tickers(
        self,
        *,
        cvm_code: str | None = None,
        cnpj: str | None = None,
        active_only: bool = True,
        as_of: date | None = None,
    ) -> tuple[str, ...]:
        if not cvm_code and not cnpj:
            raise ValueError("cvm_code or cnpj is required")

        clauses: list[str] = []
        values: list[str] = []
        if cvm_code:
            clauses.append("i.cvm_code = ?")
            values.append(_normalize_cvm_code(cvm_code))
        if cnpj:
            clauses.append("i.cnpj = ?")
            values.append(_normalize_cnpj(cnpj))

        target = (as_of or date.today()).isoformat()
        active_clause = ""
        if active_only:
            active_clause = """
                AND (s.trading_start IS NULL OR s.trading_start <= ?)
                AND (s.trading_end IS NULL OR s.trading_end >= ?)
            """
            values.extend([target, target])

        query = f"""
            SELECT DISTINCT s.ticker
            FROM securities s
            JOIN issuers i ON i.issuer_id = s.issuer_id
            WHERE {' AND '.join(clauses)}
            {active_clause}
            ORDER BY s.ticker
        """
        with self._connect() as conn:
            rows = conn.execute(query, values).fetchall()
        return tuple(str(row["ticker"]) for row in rows)

    def resolve_issuer_by_ticker(
        self,
        ticker: str,
        *,
        as_of: date | None = None,
    ) -> Issuer | None:
        normalized = _normalize_ticker(ticker)
        if not normalized:
            raise ValueError("ticker must not be empty")
        target = (as_of or date.today()).isoformat()

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    i.issuer_id, i.cvm_code, i.cnpj, i.legal_name,
                    i.trading_name, i.registration_status
                FROM securities s
                JOIN issuers i ON i.issuer_id = s.issuer_id
                WHERE s.ticker = ?
                  AND (s.trading_start IS NULL OR s.trading_start <= ?)
                  AND (s.trading_end IS NULL OR s.trading_end >= ?)
                ORDER BY COALESCE(s.reference_date, '') DESC, i.issuer_id
                LIMIT 1
                """,
                (normalized, target, target),
            ).fetchone()

        return _issuer_from_row(row) if row else None

    def securities_for_issuer(
        self,
        issuer_id: str,
        *,
        active_only: bool = True,
        as_of: date | None = None,
    ) -> tuple[Security, ...]:
        values: list[str] = [issuer_id]
        active_clause = ""
        if active_only:
            target = (as_of or date.today()).isoformat()
            active_clause = """
                AND (trading_start IS NULL OR trading_start <= ?)
                AND (trading_end IS NULL OR trading_end >= ?)
            """
            values.extend([target, target])

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    instrument_id, ticker, issuer_id, asset_type, description,
                    market, exchange_name, trading_start, trading_end,
                    reference_date
                FROM securities
                WHERE issuer_id = ?
                {active_clause}
                ORDER BY ticker
                """,
                values,
            ).fetchall()
        return tuple(_security_from_row(row) for row in rows)

    def get_issuer(self, issuer_id: str) -> Issuer | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    issuer_id, cvm_code, cnpj, legal_name,
                    trading_name, registration_status
                FROM issuers
                WHERE issuer_id = ?
                """,
                (issuer_id,),
            ).fetchone()
        return _issuer_from_row(row) if row else None


def _issuer_id(record: CvmOpenDataIssuerRecord) -> str | None:
    if record.cvm_code:
        return f"cvm:{_normalize_cvm_code(record.cvm_code)}"
    if record.cnpj:
        return f"cnpj:{_normalize_cnpj(record.cnpj)}"
    return None


def _issuer_rank(record: CvmOpenDataIssuerRecord) -> tuple[int, str]:
    status = (record.registration_status or "").casefold()
    active = int("ativ" in status)
    return active, record.cvm_code or ""


def _security_rank(record: CvmOpenDataSecurityRecord) -> tuple[date, date]:
    return (
        record.reference_date or date.min,
        record.trading_end or date.max,
    )


def _normalize_cnpj(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    return digits


def _normalize_cvm_code(value: str) -> str:
    text = value.strip()
    if text.endswith(".0"):
        text = text[:-2]
    digits = re.sub(r"\D", "", text)
    return digits.lstrip("0") or "0"


def _normalize_ticker(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().upper())


def _date_text(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _issuer_from_row(row: sqlite3.Row) -> Issuer:
    return Issuer(
        issuer_id=str(row["issuer_id"]),
        cvm_code=row["cvm_code"],
        cnpj=row["cnpj"],
        legal_name=str(row["legal_name"]),
        trading_name=row["trading_name"],
        registration_status=row["registration_status"],
    )


def _security_from_row(row: sqlite3.Row) -> Security:
    return Security(
        instrument_id=str(row["instrument_id"]),
        ticker=str(row["ticker"]),
        issuer_id=str(row["issuer_id"]),
        asset_type=row["asset_type"],
        description=row["description"],
        market=row["market"],
        exchange=row["exchange_name"],
        trading_start=_parse_date(row["trading_start"]),
        trading_end=_parse_date(row["trading_end"]),
        reference_date=_parse_date(row["reference_date"]),
    )
