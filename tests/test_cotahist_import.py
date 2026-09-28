from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
import zipfile

import pytest

from b3_agent.ingestion.cotahist import import_cotahist_zip, parse_cotahist_line
from b3_agent.repositories.market_data import MarketDataRepository


def quote(ticker="PETR4", date="20260925", factor=1, market="010"):
    row = bytearray(b" " * 245)

    def put(start, end, value):
        data = str(value).encode("ascii")
        assert len(data) <= end - start
        row[start:end] = data.ljust(end - start, b" ")

    def number(start, end, value):
        row[start:end] = f"{value:0{end-start}d}".encode("ascii")

    put(0, 2, "01")
    put(2, 10, date)
    put(10, 12, "02")
    put(12, 24, ticker)
    put(24, 27, market)
    put(52, 56, "R$")
    for start, end, amount in ((56, 69, 2900), (69, 82, 3100),
                               (82, 95, 2800), (95, 108, 2950),
                               (108, 121, 3000)):
        number(start, end, amount)
    number(152, 170, 123456)
    number(210, 217, factor)
    put(230, 242, "BRPETRACNPR6")
    return bytes(row)


def annual_zip(path, line):
    header = b"00COTAHIST.2026" + b" " * 230
    trailer = b"99" + b" " * 243
    with zipfile.ZipFile(path, "w") as output:
        output.writestr("COTAHIST.2026.TXT", b"\r\n".join((header, line, trailer)) + b"\r\n")


def test_parser_reads_fixed_width_raw_prices_and_quotation_factor():
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    record = parse_cotahist_line(quote(factor=1000), {"PETR4"}, now)
    assert record.close == 0.03
    assert record.volume == 123456
    assert record.adjusted_close is None
    assert record.quality_flags == ("UNADJUSTED", "AVAILABILITY_ESTIMATED")
    assert record.available_timestamp > record.observation_timestamp
    assert record.observation_timestamp.date() == date(2026, 9, 25)
    assert parse_cotahist_line(quote(market="070"), {"PETR4"}, now) is None
    assert parse_cotahist_line(quote(), {"VALE3"}, now) is None


def test_zip_import_is_offline_dry_run_then_idempotent(tmp_path):
    source = tmp_path / "COTAHIST_A2026.ZIP"
    annual_zip(source, quote())
    archive = tmp_path / "archive"
    assert import_cotahist_zip(source, {"PETR4"}, archive) == {"PETR4": 1}
    assert not archive.exists()
    for _ in range(2):
        assert import_cotahist_zip(source, {"PETR4"}, archive, dry_run=False) == {"PETR4": 1}
    rows = MarketDataRepository(archive).read("PETR4")
    assert len(rows) == 1
    assert rows[0].close == 30.0
    assert rows[0].source == "b3_cotahist"
    assert rows[0].observation_timestamp.date() == date(2026, 9, 25)


def test_reimport_replaces_legacy_utc_shifted_record(tmp_path):
    source = tmp_path / "COTAHIST_A2026.ZIP"
    annual_zip(source, quote())
    archive = tmp_path / "archive"
    previous = parse_cotahist_line(
        quote(), {"PETR4"}, datetime(2026, 9, 28, tzinfo=timezone.utc)
    )
    # Recreate the previous importer behavior: 23:59 São Paulo became Sep 26 UTC.
    legacy = replace(
        previous,
        observation_timestamp=datetime(2026, 9, 26, 2, 59, 59, tzinfo=timezone.utc),
    )
    MarketDataRepository(archive).write([legacy])

    import_cotahist_zip(source, {"PETR4"}, archive, dry_run=False)
    rows = MarketDataRepository(archive).read("PETR4")
    assert len(rows) == 1
    assert rows[0].observation_timestamp.date() == date(2026, 9, 25)


def test_import_rejects_incomplete_archive(tmp_path):
    source = tmp_path / "invalid.zip"
    with zipfile.ZipFile(source, "w") as output:
        output.writestr("COTAHIST.2026.TXT", b"00COTAHIST.2026" + b" " * 230 + b"\n" + quote())
    with pytest.raises(ValueError, match="trailer is missing"):
        import_cotahist_zip(source, {"PETR4"}, tmp_path / "archive")
