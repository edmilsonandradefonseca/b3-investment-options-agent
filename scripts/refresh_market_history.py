#!/usr/bin/env python3
"""Refresh the shared B3 daily OHLCV archive from official COTAHIST ZIPs.

The selected universe is the current portfolio's stock/option underlyings plus
B3_INTEL_WATCHLIST. Only aggregate, symbol-redacted metrics are written to the
runner summary because the GitHub Actions log is public.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _load_watchlist_environment() -> None:
    """Read only the watchlist setting from the same env files used by systemd."""
    if os.getenv("B3_INTEL_WATCHLIST"):
        return
    candidates = (
        Path("/opt/joao-runtime/joao.env"),
        Path("/etc/b3-runtime.env"),
        Path("/opt/b3-runtime/b3.env"),
    )
    for path in candidates:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            match = re.match(r"^\s*B3_INTEL_WATCHLIST\s*=\s*(.*?)\s*$", line)
            if match:
                value = match.group(1)
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                os.environ["B3_INTEL_WATCHLIST"] = value
                return


_load_watchlist_environment()

from b3_agent.config import settings
from b3_agent.ingestion.cotahist import import_cotahist_zip
from b3_agent.jobs.continuous_intelligence import _monitored_tickers
from b3_agent.repositories.market_data import MarketDataRepository
from b3_agent.strategy_live import _validated_equity_ticker

_SAO_PAULO = ZoneInfo("America/Sao_Paulo")
_B3_URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP"


def _selected_tickers() -> tuple[str, ...]:
    selected: list[str] = []
    for raw in _monitored_tickers():
        try:
            ticker = _validated_equity_ticker(raw)
        except (TypeError, ValueError):
            continue
        if ticker not in selected:
            selected.append(ticker)
    return tuple(selected)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _download_year(year: int, download_dir: Path) -> tuple[Path, str, bool]:
    """Download/refresh one official archive, honoring validators when available."""
    download_dir.mkdir(parents=True, exist_ok=True)
    archive = download_dir / f"COTAHIST_A{year}.ZIP"
    metadata_path = download_dir / f"COTAHIST_A{year}.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        metadata = {}
    headers = {"User-Agent": "b3-investment-options-agent/1.0"}
    if metadata.get("etag"):
        headers["If-None-Match"] = str(metadata["etag"])
    if metadata.get("last_modified"):
        headers["If-Modified-Since"] = str(metadata["last_modified"])
    request = urllib.request.Request(_B3_URL.format(year=year), headers=headers)
    try:
        response = urllib.request.urlopen(request, timeout=180)
    except urllib.error.HTTPError as exc:
        if exc.code != 304:
            raise
        if not archive.is_file():
            raise RuntimeError("B3 returned not-modified without a cached archive") from exc
        return archive, _sha256(archive), False

    with response:
        fd, temp_name = tempfile.mkstemp(prefix=f".cotahist-{year}-", suffix=".zip", dir=download_dir)
        os.close(fd)
        temporary = Path(temp_name)
        try:
            with temporary.open("wb") as target:
                while block := response.read(1024 * 1024):
                    target.write(block)
            with zipfile.ZipFile(temporary) as zipped:
                if zipped.testzip() is not None:
                    raise ValueError("B3 archive failed ZIP integrity validation")
            digest = _sha256(temporary)
            temporary.replace(archive)
            _atomic_json(
                metadata_path,
                {
                    "etag": response.headers.get("ETag"),
                    "last_modified": response.headers.get("Last-Modified"),
                    "sha256": digest,
                },
            )
        finally:
            temporary.unlink(missing_ok=True)
    return archive, digest, True


def _import_if_needed(
    year: int, archive: Path, archive_sha: str, tickers: set[str], data_root: Path,
    *, retry_missing: bool,
) -> tuple[int, bool]:
    """Import unprocessed ticker/archive pairs; retry unresolved current-year symbols."""
    marker_dir = data_root / "derived" / "market_history_refresh" / "imports"
    marker_dir.mkdir(parents=True, exist_ok=True)
    pending = {
        ticker for ticker in tickers
        if retry_missing or not (marker_dir / f"{year}-{archive_sha}-{ticker}.json").exists()
    }
    if not pending:
        return 0, False
    destination = data_root / "archive" / "cotahist_raw"
    counts = import_cotahist_zip(archive, pending, destination, dry_run=True)
    matched = {ticker for ticker, count in counts.items() if count > 0}
    imported = 0
    if matched:
        applied = import_cotahist_zip(archive, matched, destination, dry_run=False)
        imported = sum(applied.values())
    for ticker in matched:
        _atomic_json(
            marker_dir / f"{year}-{archive_sha}-{ticker}.json",
            {"year": year, "archive_sha256": archive_sha, "records_imported": counts[ticker]},
        )
    # A prior-year annual archive is complete and immutable. Cache no-match there;
    # keep retrying current-year no-matches as B3 publishes new daily data.
    if not retry_missing:
        for ticker in pending - matched:
            _atomic_json(
                marker_dir / f"{year}-{archive_sha}-{ticker}.json",
                {"year": year, "archive_sha256": archive_sha, "records_imported": 0},
            )
    return imported, bool(matched)


def _prune_retention(data_root: Path, ticker_set: set[str], cutoff) -> int:
    """Keep the canonical rolling 360-calendar-day OHLCV window."""
    repository = MarketDataRepository(data_root / "archive" / "cotahist_raw")
    removed = 0
    for ticker in ticker_set:
        rows = repository.read(ticker)
        kept = [
            row for row in rows
            if row.observation_timestamp.astimezone(_SAO_PAULO).date() >= cutoff
        ]
        removed += len(rows) - len(kept)
        if kept and len(kept) != len(rows):
            repository.write(kept)
    return removed


def _summary_path(data_root: Path) -> Path:
    return data_root / "derived" / "market_history_refresh" / "latest.json"


def main() -> int:
    now = datetime.now(_SAO_PAULO)
    data_root = settings.data_dir
    tickers = _selected_tickers()
    summary: dict[str, object] = {
        "source": "B3_COTAHIST",
        "started_at": now.isoformat(),
        "status": "FAILED",
        "ticker_count": len(tickers),
        "ticker_count_with_history": 0,
        "record_count": 0,
        "retention_days": 360,
        "years": [],
        "refreshed_archive_count": 0,
        "error_type": None,
    }
    try:
        if not tickers:
            summary["status"] = "NO_VALID_TICKERS"
            return _finish(summary, data_root, 2)
        tickers_set = set(tickers)
        current_year = now.year
        years = (current_year - 1, current_year)
        summary["years"] = list(years)
        download_dir = data_root / "archive" / "cotahist_downloads"
        imported_records = 0
        for year in years:
            archive, archive_sha, _downloaded = _download_year(year, download_dir)
            imported, changed = _import_if_needed(
                year, archive, archive_sha, tickers_set, data_root,
                retry_missing=(year == current_year),
            )
            imported_records += imported
            if changed:
                summary["refreshed_archive_count"] = int(summary["refreshed_archive_count"]) + 1

        cutoff = now.date() - timedelta(days=359)
        summary["pruned_record_count"] = _prune_retention(data_root, tickers_set, cutoff)
        repository = MarketDataRepository(data_root / "archive" / "cotahist_raw")
        counts = [len(repository.read(ticker)) for ticker in tickers]
        summary["ticker_count_with_history"] = sum(count > 0 for count in counts)
        summary["record_count"] = sum(counts)
        summary["imported_record_count"] = imported_records
        summary["cutoff_date"] = cutoff.isoformat()
        summary["completed_at"] = datetime.now(_SAO_PAULO).isoformat()
        summary["status"] = "PASS" if all(count > 0 for count in counts) else "PARTIAL_MISSING_HISTORY"
        return _finish(summary, data_root, 0 if summary["status"] == "PASS" else 2)
    except Exception as exc:  # Persist a redacted failure record; no ticker/provider values in logs.
        summary["error_type"] = type(exc).__name__
        summary["completed_at"] = datetime.now(_SAO_PAULO).isoformat()
        return _finish(summary, data_root, 2)


def _finish(summary: dict[str, object], data_root: Path, exit_code: int) -> int:
    _atomic_json(_summary_path(data_root), summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
