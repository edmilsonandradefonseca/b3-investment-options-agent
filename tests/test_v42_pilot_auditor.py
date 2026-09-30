from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path


script_path = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "summarize_intelligence_pilot_20.py"
)
spec = spec_from_file_location("summarize_intelligence_pilot_20", script_path)
summary = module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(summary)


TICKERS = (
    "ABEV3", "ASAI3", "BBDC4", "BEEF3", "CMIG4", "CURY3", "DIRR3", "EQTL3",
    "GGBR4", "ITUB4", "MILS3", "ORVR3", "PCAR3", "PETR4", "POMO4", "RANI3",
    "SUZB3", "TOTS3", "VULC3", "WEGE3",
)
ROUTES = {
    "market": "market_provider",
    "research": "deepseek-r1:8b",
    "senior": "openclaw",
}


def _write_detail(root: Path, ticker: str, research: str, senior: str) -> None:
    evidence = {
        "evidence_conclusion": (
            "MATERIAL_FOUND"
            if research == "completed"
            else "NO_MATERIAL_FOUND"
            if research == "skipped_no_material_events"
            else "COVERAGE_INSUFFICIENT"
        ),
        "source_refs": (
            ["https://example.test/event"]
            if research == "completed"
            else []
        ),
        "dated_result_count": 2 if research != "coverage_insufficient" else 0,
        "dated_recent_count": 2 if research != "coverage_insufficient" else 0,
        "raw_result_count": 8,
        "acquisition_status": "PARTIAL",
        "fallback_used": research == "coverage_insufficient",
        "fallback_strategy": (
            "general_unbounded"
            if research == "coverage_insufficient"
            else None
        ),
        "engine_errors": [],
    }
    payload = {
        "ticker": ticker,
        "routes": ROUTES,
        "market": {
            "as_of": "2026-09-30T00:00:00+00:00",
            "source": "b3_cotahist",
        },
        "deepseek_status": research,
        "openclaw_status": senior,
        "evidence": evidence,
    }
    (root / f"{ticker}.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_auditor_accepts_exact_10_material_5_no_material_5_coverage_gap_shape(tmp_path):
    rows = []
    for index, ticker in enumerate(TICKERS):
        if index < 10:
            research, senior = "completed", "completed"
        elif index < 15:
            research, senior = "skipped_no_material_events", "not_required"
        else:
            research, senior = "coverage_insufficient", "not_required"

        rows.append(
            {
                "ticker": ticker,
                "deepseek": research,
                "openclaw": senior,
            }
        )
        _write_detail(tmp_path, ticker, research, senior)

    manifest = {
        "requested": 20,
        "results": rows,
        "router_verified": 20,
        "market_validated": 20,
        "official_sources": {
            "status": "SUCCESS",
            "resolved_tickers": 20,
            "ipe_document_count": 2284,
            "ipe_material_count": 107,
        },
    }
    (tmp_path / "latest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    report = summary.evaluate(tmp_path)

    assert report["status"] == "PASS_WITH_COVERAGE_GAPS"
    assert report["stocks"] == 20
    assert report["deepseek_completed"] == 10
    assert report["openclaw_escalations_completed"] == 10
    assert report["skipped_no_material_events"] == 5
    assert report["coverage_insufficient"] == 5
    assert len(report["coverage_gaps"]) == 5
    assert not report["issues"]


def test_auditor_keeps_true_execution_failures_as_limited(tmp_path):
    rows = []
    for ticker in TICKERS:
        research, senior = "skipped_no_material_events", "not_required"
        rows.append(
            {
                "ticker": ticker,
                "deepseek": research,
                "openclaw": senior,
            }
        )
        _write_detail(tmp_path, ticker, research, senior)

    rows[-1]["deepseek"] = "failed"
    detail = json.loads((tmp_path / f"{TICKERS[-1]}.json").read_text())
    detail["deepseek_status"] = "failed"
    (tmp_path / f"{TICKERS[-1]}.json").write_text(
        json.dumps(detail),
        encoding="utf-8",
    )

    (tmp_path / "latest.json").write_text(
        json.dumps(
            {
                "requested": 20,
                "results": rows,
                "router_verified": 20,
                "market_validated": 20,
                "official_sources": {
                    "status": "SUCCESS",
                    "resolved_tickers": 20,
                },
            }
        ),
        encoding="utf-8",
    )

    report = summary.evaluate(tmp_path)

    assert report["status"] == "LIMITED"
    assert any("research status failed" in issue for issue in report["issues"])
