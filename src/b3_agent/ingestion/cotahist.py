"""Offline import of B3's fixed-width COTAHIST annual ZIP archives.

This archive contains unadjusted historical prices and is kept separate from
the BRAPI operational cache. It is not a total-return or live quote source.
"""

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import zipfile

from b3_agent.repositories.market_data import MarketDataRepository
from b3_agent.schemas.market import StockMarketData


_SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def parse_cotahist_line(line: bytes, tickers: set[str], ingested_at: datetime) -> StockMarketData | None:
    """Parse one 245-byte quote record using B3's published 2017 layout."""
    row = line.rstrip(b"\r\n")
    if len(row) != 245:
        raise ValueError(f"COTAHIST record has {len(row)} bytes, expected 245")
    if row[:2] != b"01" or row[24:27] != b"010":
        return None  # header, trailer and non-cash-market instruments
    ticker = row[12:24].decode("ascii").strip().upper()
    if ticker not in tickers:
        return None
    if row[52:56].decode("ascii").strip() != "R$":
        raise ValueError(f"unsupported historical currency for {ticker}")
    observed_date = date.fromisoformat(row[2:10].decode("ascii"))
    factor = int(row[210:217])
    if factor <= 0:
        raise ValueError(f"invalid quotation factor for {ticker}")

    def price(start: int, end: int) -> float:
        return int(row[start:end]) / (100 * factor)

    close = price(108, 121)
    if close <= 0:
        raise ValueError(f"invalid closing price for {ticker}")
    # Publication time is not in COTAHIST; the following midnight is a
    # conservative approximation and is explicitly flagged below.
    observed = datetime.combine(observed_date, time(23, 59, 59), _SAO_PAULO).astimezone(timezone.utc)
    available = datetime.combine(observed_date + timedelta(days=1), time.min, _SAO_PAULO).astimezone(timezone.utc)
    return StockMarketData(
        instrument_id=ticker,
        ticker=ticker,
        observation_timestamp=observed,
        available_timestamp=available,
        source="b3_cotahist",
        ingested_at=ingested_at,
        source_record_id=f"{ticker}:{observed_date.isoformat()}:{row[230:242].decode('ascii').strip()}",
        quality_flags=("UNADJUSTED", "AVAILABILITY_ESTIMATED"),
        open=price(56, 69), high=price(69, 82), low=price(82, 95),
        close=close, vwap=price(95, 108), volume=float(int(row[152:170])),
        adjusted_close=None,
        currency="BRL",
    )


def import_cotahist_zip(
    zip_path: Path, tickers: set[str], archive_dir: Path, *, dry_run: bool = True
) -> dict[str, int]:
    """Stream a local B3 ZIP and merge selected tickers into raw-price Parquet."""
    selected = {ticker.strip().upper() for ticker in tickers if ticker.strip()}
    if not selected:
        raise ValueError("at least one ticker is required")
    parsed: dict[str, dict[date, StockMarketData]] = defaultdict(dict)
    ingested_at = datetime.now(timezone.utc)
    with zipfile.ZipFile(zip_path) as archive:
        members = [name for name in archive.namelist() if name.upper().endswith(".TXT")]
        if len(members) != 1:
            raise ValueError("expected exactly one annual TXT member")
        with archive.open(members[0]) as stream:
            first = stream.readline()
            if len(first.rstrip(b"\r\n")) != 245 or not first.startswith(b"00COTAHIST."):
                raise ValueError("COTAHIST header is invalid")
            trailer_found = False
            for line in stream:
                if line.startswith(b"99"):
                    if len(line.rstrip(b"\r\n")) != 245:
                        raise ValueError("COTAHIST trailer is invalid")
                    trailer_found = True
                    break
                record = parse_cotahist_line(line, selected, ingested_at)
                if record:
                    parsed[record.ticker][record.observation_timestamp.date()] = record
            if not trailer_found:
                raise ValueError("COTAHIST trailer is missing")
    counts = {ticker: len(records) for ticker, records in sorted(parsed.items())}
    if dry_run:
        return counts
    repository = MarketDataRepository(archive_dir)
    for ticker, records in parsed.items():
        old = {
            record.observation_timestamp.date(): record
            for record in repository.read(ticker)
        }
        old.update(records)
        repository.write([old[day] for day in sorted(old)])
    return counts
