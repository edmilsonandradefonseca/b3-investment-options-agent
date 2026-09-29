#!/usr/bin/env python3
"""Evidence-backed 20-stock pilot for local DeepSeek and OpenClaw senior reasoning.

Run under the B3 systemd environment. Results are research artifacts, never
canonical rankings, valuations, or investment recommendations.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from b3_agent.config import settings
from b3_agent.jobs.nightly_intelligence import NightlyIntelligenceJob
from b3_agent.llm.client import OpenClawStructuredClient
from b3_agent.orchestration.live_providers import LiveProviderService
from b3_agent.routing import FastRouter, RouteTarget

TICKERS = (
    "ABEV3", "ASAI3", "BBDC4", "BEEF3", "CMIG4", "CURY3", "DIRR3", "EQTL3",
    "GGBR4", "ITUB4", "MILS3", "ORVR3", "PCAR3", "PETR4", "POMO4", "RANI3",
    "SUZB3", "TOTS3", "VULC3", "WEGE3",
)
SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "risks": {"type": "array", "items": {"type": "string"}},
        "catalysts": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "risks", "catalysts", "limitations", "evidence_refs"],
    "additionalProperties": False,
}


def save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temp.replace(path)


def routing_contract(ticker: str) -> dict[str, str]:
    """Prove all three V4.1 routes for each covered stock before doing work."""
    router = FastRouter()
    paths = {
        "market": router.route(f"qual o preço de {ticker}?", metadata={"ticker": ticker}),
        "research": router.route(source="scheduler", task_type="b3.news.nightly", metadata={"ticker": ticker}),
        "senior": router.route(f"vale a pena rever a tese de {ticker}?", metadata={"ticker": ticker}),
    }
    expected = {
        "market": RouteTarget.MARKET_PROVIDER,
        "research": RouteTarget.DEEPSEEK_BACKGROUND,
        "senior": RouteTarget.OPENCLAW,
    }
    for name, decision in paths.items():
        if decision.target != expected[name]:
            raise RuntimeError(f"V4.1 router mismatch for {ticker}/{name}: {decision.target}")
    return {name: decision.target.value for name, decision in paths.items()}


def market_evidence(ticker: str) -> dict:
    today = datetime.now(timezone.utc).date()
    records = LiveProviderService().market_provider.get_market_data(
        ticker, today - timedelta(days=35), today
    )
    if not records:
        raise RuntimeError(f"No dated market record for {ticker}")
    latest = max(records, key=lambda item: item.observation_timestamp)
    return {
        "close": latest.close, "volume": latest.volume,
        "as_of": latest.observation_timestamp.isoformat(),
        "source": latest.source, "source_record_id": latest.source_record_id,
    }


def analyze(ticker: str, output: Path, senior: OpenClawStructuredClient) -> dict:
    path = output / f"{ticker}.json"
    row = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"ticker": ticker}
    row["routes"] = routing_contract(ticker)
    today = datetime.now(timezone.utc).date().isoformat()
    if row.get("run_date") != today:
        try:
            market = market_evidence(ticker)
            market_error = None
        except Exception as exc:
            market = None
            market_error = f"{type(exc).__name__}: {exc}"
        # V4.1 UC-10: search -> dated research events -> material prefilter -> local DeepSeek.
        result = NightlyIntelligenceJob(
            news_limit=8, max_deepseek_calls=1, output_dir=output / "deepseek"
        ).run(tickers=[ticker])["results"][0]
        row = {
            "ticker": ticker, "run_date": today, "routes": routing_contract(ticker),
            "market": market, "market_error": market_error,
            "evidence": {
                "collected_at": result.get("as_of"),
                "source_refs": result.get("source_refs", []),
                "news": result.get("evidence_events", []),
            },
            "deepseek_status": result["status"],
            "deepseek": {
                "model": result.get("model"), "analysis": result.get("analysis"),
                "eval_count": result.get("eval_count"),
            } if result["status"] == "completed" else None,
            "deepseek_error": result.get("error"),
            "escalation_status": "pending" if result["status"] == "completed" else "not_required",
            "openclaw_status": "pending" if result["status"] == "completed" else "not_required",
        }
        save(path, row)

    if row.get("escalation_status") != "pending":
        return row
    facts = row["evidence"]
    refs = facts["source_refs"]
    try:
        # V4.1 senior escalation receives the source events plus DeepSeek's dossier.
        response = senior.complete_json(
            instructions=(
                "Você é a camada sênior da V4.1 para UC-10. Examine apenas eventos e "
                "a síntese local fornecidos. Não crie ranking, preço, causalidade ou "
                "recomendação. Cite apenas source_refs fornecidos e destaque incertezas."
            ),
            input_text=json.dumps({
                "ticker": ticker, "as_of": facts["collected_at"],
                "source_events": facts["news"], "deepseek_dossier": row["deepseek"],
            }, ensure_ascii=False),
            schema_name="b3_uc10_escalation_v1", schema=SCHEMA,
        )
        if not isinstance(response, dict) or any(k not in response for k in SCHEMA["required"]):
            raise ValueError("Incomplete senior analysis schema")
        if not isinstance(response["evidence_refs"], list) or not set(response["evidence_refs"]).issubset(set(refs)):
            raise ValueError("Senior analysis referenced unknown sources")
        row["openclaw"] = {"model": settings.openclaw_model, "analysis": response}
        row["openclaw_status"] = "completed"
        row["escalation_status"] = "completed"
        row.pop("openclaw_error", None)
    except Exception as exc:
        row["openclaw_status"] = "failed"
        row["escalation_status"] = "pending"
        row["openclaw_error"] = f"{type(exc).__name__}: {exc}"
    save(path, row)
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, choices=range(1, 21), metavar="1-20")
    args = parser.parse_args()
    output = settings.data_dir / "derived" / "intelligence_pilot_v41"
    senior = OpenClawStructuredClient(agent=settings.openclaw_agent, model=settings.openclaw_model,
                                      timeout=settings.openclaw_timeout_seconds, executable=settings.openclaw_bin)
    rows = []
    for ticker in TICKERS[:args.limit]:
        row = analyze(ticker, output, senior)
        rows.append({"ticker": ticker, "deepseek": row.get("deepseek_status", "not_run"),
                     "openclaw": row.get("openclaw_status", "not_run"),
                     "escalation": row.get("escalation_status"), "routes": row.get("routes"),
                     "market": "validated" if row.get("market") else "unavailable",
                     "market_error": row.get("market_error")})
        manifest = {
            "as_of": datetime.now(timezone.utc).isoformat(), "requested": args.limit,
            "router_verified": sum(bool(r["routes"]) for r in rows),
            "market_validated": sum(r["market"] == "validated" for r in rows),
            "deepseek_completed": sum(r["deepseek"] == "completed" for r in rows),
            "no_material_event": sum(r["deepseek"] == "skipped_no_material_events" for r in rows),
            "openclaw_escalations_completed": sum(r["openclaw"] == "completed" for r in rows),
            "both_completed": sum(r["deepseek"] == r["openclaw"] == "completed" for r in rows),
            "results": rows,
        }
        save(output / "latest.json", manifest)
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    return 0 if all(r["market"] == "validated" and r["deepseek"] != "failed" and r["openclaw"] != "failed" for r in rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
