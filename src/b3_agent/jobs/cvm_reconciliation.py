from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from b3_agent.config import settings
from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.jobs.cvm_open_data import CvmOpenDataBackfillJob
from b3_agent.portfolio.snapshot import load_active_snapshots


class CvmReconciliationJob:
    """Daily Open Data reconciliation against recently observed live RAD Evidence."""

    def __init__(
        self,
        *,
        registry: IssuerRegistry | None = None,
        backfill_job: CvmOpenDataBackfillJob | None = None,
        continuous_root: str | Path | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        self.registry = registry or IssuerRegistry()
        self.backfill_job = backfill_job or CvmOpenDataBackfillJob(
            registry=self.registry
        )
        self.continuous_root = Path(
            continuous_root
            or settings.data_dir / "derived" / "continuous_intelligence"
        )
        self.output_dir = Path(
            output_dir or settings.data_dir / "derived" / "cvm_reconciliation"
        )
        self.reconciled_dir = self.output_dir / "evidence"

    def run(
        self,
        *,
        year: int | None = None,
        monitored_tickers: tuple[str, ...] | list[str] | None = None,
        as_of: date | None = None,
    ) -> dict[str, Any]:
        target_date = as_of or datetime.now(timezone.utc).date()
        target_year = year or target_date.year
        lookback_days = int(
            os.getenv("B3_INTEL_RECONCILIATION_LOOKBACK_DAYS", "7")
        )
        cutoff = target_date - timedelta(days=lookback_days)
        tickers = tuple(
            dict.fromkeys(
                str(item).upper().strip()
                for item in (
                    monitored_tickers
                    if monitored_tickers is not None
                    else _portfolio_tickers()
                )
                if str(item).strip()
            )
        )
        cvm_codes = tuple(
            dict.fromkeys(
                issuer.cvm_code
                for ticker in tickers
                if (issuer := self.registry.resolve_issuer_by_ticker(ticker)) is not None
                and issuer.cvm_code
            )
        )

        open_manifest = self.backfill_job.run(
            year=target_year,
            cvm_codes=cvm_codes,
            sync_registry=True,
        )
        live_keys = self._live_semantic_keys()
        recent_rows = [
            row
            for row in open_manifest.get("disclosures", [])
            if _row_date(row) is not None and _row_date(row) >= cutoff
        ]
        missing = [
            row for row in recent_rows if semantic_key_from_row(row) not in live_keys
        ]

        reconciled = 0
        for row in missing:
            evidence = row.get("evidence")
            if not isinstance(evidence, dict):
                continue
            evidence_id = str(row.get("evidence_id") or "").strip()
            if not evidence_id:
                continue
            path = self.reconciled_dir / f"{_safe_name(evidence_id)}.json"
            if not path.exists():
                _atomic_json_write(
                    path,
                    {
                        "reconciliation_status": "HISTORICAL_RECONSTRUCTION",
                        "evidence": evidence,
                    },
                )
                reconciled += 1

        completed_at = datetime.now(timezone.utc)
        manifest = {
            "status": "PASS",
            "completed_at": completed_at.isoformat(),
            "year": target_year,
            "lookback_days": lookback_days,
            "monitored_tickers": list(tickers),
            "cvm_codes": list(cvm_codes),
            "open_data_recent": len(recent_rows),
            "live_semantic_keys": len(live_keys),
            "missing_from_live": len(missing),
            "reconciled_new": reconciled,
            "pit_rule": "HISTORICAL_RECONSTRUCTION_NEVER_OBSERVED_LIVE",
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        _atomic_json_write(self.output_dir / "latest.json", manifest)
        runs = self.output_dir / "runs"
        stamp = completed_at.strftime("%Y%m%dT%H%M%S%fZ")
        _atomic_json_write(runs / f"{stamp}.json", manifest)
        return manifest

    def _live_semantic_keys(self) -> set[str]:
        evidence_dir = self.continuous_root / "evidence"
        keys: set[str] = set()
        if not evidence_dir.is_dir():
            return keys
        for path in evidence_dir.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            evidence = payload.get("evidence")
            if isinstance(evidence, dict):
                keys.add(semantic_key_from_evidence(evidence))
        return keys


def semantic_key_from_row(row: dict[str, Any]) -> str:
    return "|".join(
        [
            str(row.get("cvm_code") or ""),
            str(row.get("reference_date") or ""),
            _norm(row.get("category")),
            _norm(row.get("disclosure_type")),
            _norm(row.get("species")),
        ]
    )


def semantic_key_from_evidence(evidence: dict[str, Any]) -> str:
    metadata = evidence.get("metadata") or {}
    extra = metadata.get("extra") or {}
    reference_at = str(metadata.get("reference_at") or "")
    reference_date = reference_at[:10] if reference_at else ""
    return "|".join(
        [
            str(metadata.get("cvm_code") or ""),
            reference_date,
            _norm(extra.get("category")),
            _norm(extra.get("disclosure_type")),
            _norm(extra.get("species")),
        ]
    )


def _row_date(row: dict[str, Any]) -> date | None:
    for key in ("delivered_at", "reference_date"):
        value = str(row.get(key) or "")
        if not value:
            continue
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            continue
    return None


def _portfolio_tickers() -> tuple[str, ...]:
    snapshots = load_active_snapshots(settings.data_dir)
    portfolio = snapshots.get("portfolio_context")
    if portfolio is None:
        return ()
    tickers: list[str] = []
    for position in portfolio.positions:
        value = (
            position.underlying_ticker
            if position.instrument_type == "OPTION" and position.underlying_ticker
            else position.ticker
        )
        ticker = str(value).upper().strip()
        if ticker and ticker not in tickers:
            tickers.append(ticker)
    return tuple(tickers)


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _safe_name(value: str) -> str:
    import hashlib
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temp.replace(path)
