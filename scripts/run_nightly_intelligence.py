#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from b3_agent.config import settings
from b3_agent.intelligence.official_sources import load_open_data_official_evidence
from b3_agent.jobs.nightly_intelligence import NightlyIntelligenceJob
from b3_agent.jobs.continuous_intelligence import _monitored_tickers
from b3_agent.strategy_live import _validated_equity_ticker


def partition_monitored_tickers(values: Iterable[object]) -> tuple[list[str], list[str]]:
    """Return canonical equity tickers and redacted stable hashes for rejected identities."""
    valid: list[str] = []
    rejected_hashes: list[str] = []
    seen_valid: set[str] = set()
    seen_rejected: set[str] = set()
    for value in values:
        raw = str(value).strip().upper()
        if not raw:
            continue
        try:
            ticker = _validated_equity_ticker(raw)
        except ValueError:
            identity_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
            if identity_hash not in seen_rejected:
                rejected_hashes.append(identity_hash)
                seen_rejected.add(identity_hash)
            continue
        if ticker not in seen_valid:
            valid.append(ticker)
            seen_valid.add(ticker)
    return valid, rejected_hashes


def _coverage_summary(coverage: dict[str, Any]) -> dict[str, Any]:
    summary = {
        key: coverage[key]
        for key in ("status", "requested_tickers", "resolved_tickers")
        if isinstance(coverage.get(key), (str, int, float, bool, type(None)))
    }
    unresolved = coverage.get("unresolved_tickers")
    if isinstance(unresolved, (list, tuple)):
        summary["unresolved_ticker_count"] = len(unresolved)
    return summary


def _batch_summary(payload: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    batch_count = 0
    for batch in payload.get("batches", []):
        batch_count += 1
        for row in batch.get("results", []):
            status = row.get("status", "UNKNOWN")
            counts[status] = counts.get(status, 0) + 1
    return {"batch_count": batch_count, "result_status_counts": counts}


def _safe_target_refresh_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload[key]
        for key in ("status", "projected", "records", "accepted", "skipped", "failed")
        if isinstance(payload.get(key), (str, int, float, bool, type(None)))
    }


def _persist_runner_summary(summary: dict[str, Any]) -> None:
    path = settings.data_dir / "derived" / "nightly_intelligence" / "runner_latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", action="append", dest="tickers")
    parser.add_argument("--news-limit", type=int, default=8)
    args = parser.parse_args()

    requested = args.tickers if args.tickers is not None else _monitored_tickers()
    selected, rejected_hashes = partition_monitored_tickers(requested)
    identity_filter = {
        "accepted_ticker_count": len(selected),
        "rejected_identity_count": len(rejected_hashes),
        "rejected_identity_sha256_prefixes": rejected_hashes,
    }
    if not selected:
        summary = {"status": "NO_VALID_TICKERS", "identity_filter": identity_filter}
        _persist_runner_summary(summary)
        print(json.dumps(summary, ensure_ascii=False))
        return 2

    try:
        official_snapshot = load_open_data_official_evidence(selected)
        official_map = official_snapshot.by_ticker
        official_coverage = official_snapshot.coverage
    except Exception as exc:
        official_map = {}
        official_coverage = {
            "status": "FAILED",
            "requested_tickers": len(selected),
            "resolved_tickers": 0,
            "error_type": type(exc).__name__,
        }

    result = NightlyIntelligenceJob(
        news_limit=args.news_limit,
        local_analysis_mode="enqueue",
    ).run(
        tickers=selected,
        official_evidence_by_ticker=official_map,
    )
    from b3_agent.jobs.primary_targets import PrimaryTargetRefreshJob

    reviewed = ROOT / "docs" / "research" / "institution_targets_reviewed.json"
    target_refresh = (
        PrimaryTargetRefreshJob().run(reviewed, tickers=selected)
        if reviewed.exists()
        else {"status": "NO_REVIEWED_SOURCES"}
    )
    from b3_agent.jobs.dividend_refresh import DividendRefreshJob
    from b3_agent.jobs.institution_target_discovery import InstitutionTargetDiscoveryJob

    target_discovery = {
        "batches": [
            InstitutionTargetDiscoveryJob().run(selected[index : index + 20])
            for index in range(0, len(selected), 20)
        ]
    }
    dividend_refresh = {
        "batches": [
            DividendRefreshJob().run(selected[index : index + 20])
            for index in range(0, len(selected), 20)
        ]
    }

    dividend_projection_ok = all(
        row.get("status") == "PROJECTED"
        for batch in dividend_refresh["batches"]
        for row in batch["results"]
    )
    discovery_projection_ok = all(
        row.get("status") != "PROJECTION_FAILED"
        for batch in target_discovery["batches"]
        for row in batch["results"]
    )
    official_ok = official_coverage.get("status") == "SUCCESS"
    pipeline_ok = (
        official_ok
        and not result["failed"]
        and dividend_projection_ok
        and discovery_projection_ok
    )
    summary = {
        "status": (
            "PASS_WITH_REJECTED_IDENTITIES"
            if pipeline_ok and rejected_hashes
            else "PASS"
            if pipeline_ok
            else "PARTIAL"
        ),
        "identity_filter": identity_filter,
        "ticker_count": result["ticker_count"],
        "completed": result["completed"],
        "skipped": result["skipped"],
        "deferred": result["deferred"],
        "coverage_insufficient": result["coverage_insufficient"],
        "failed": result["failed"],
        "deepseek_calls": result["deepseek_calls"],
        "local_analysis_mode": result["local_analysis_mode"],
        "local_analysis_enqueues": result["local_analysis_enqueues"],
        "queued_local_analysis": result["queued_local_analysis"],
        "official_sources": _coverage_summary(official_coverage),
        "institution_target_discovery": _batch_summary(target_discovery),
        "issuer_dividend_refresh": _batch_summary(dividend_refresh),
        "institution_target_refresh": _safe_target_refresh_summary(target_refresh),
        "as_of": result["as_of"],
    }
    _persist_runner_summary(summary)
    print(json.dumps(summary, ensure_ascii=False))

    # Invalid monitored identities are counted and excluded from downstream
    # equity-only providers; valid assets still complete their scheduled refresh.
    return 0 if pipeline_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
