#!/usr/bin/env python3
"""Evidence-backed 20-stock pilot for local DeepSeek and OpenClaw senior reasoning.

Run under the B3 systemd environment. Results are research artifacts, never
canonical rankings, valuations, or investment recommendations.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from b3_agent.config import settings
from b3_agent.llm.client import OpenClawStructuredClient
from b3_agent.llm.ollama_client import OllamaClient
from b3_agent.orchestration.live_providers import LiveProviderService
from b3_agent.providers.searxng_news import SearxngNewsAdapter

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


def evidence_for(ticker: str) -> dict:
    now = datetime.now(timezone.utc)
    market = LiveProviderService().market_provider.get_market_data(
        ticker, (now - timedelta(days=35)).date(), now.date()
    )
    if not market:
        raise RuntimeError("No dated canonical/local or BRAPI market records")
    latest = max(market, key=lambda row: row.observation_timestamp)
    # Search failure must not erase valid market evidence; record the limitation.
    news_error = None
    try:
        news = SearxngNewsAdapter(base_url=os.getenv("B3_SEARXNG_URL", "http://127.0.0.1:8080")).search(
            ticker, query=f"{ticker} B3 resultado dividendo fato relevante", limit=8
        )
    except (OSError, ValueError) as exc:
        news = ()
        news_error = f"{type(exc).__name__}: {exc}"
    dated = [n for n in news if n.published_date and n.published_date <= now.date()]
    return {
        "ticker": ticker, "collected_at": now.isoformat(),
        "latest_market_record": {
            "close": latest.close,
            "volume": latest.volume,
            "observation_timestamp": latest.observation_timestamp.isoformat(),
            "source": latest.source,
            "source_record_id": latest.source_record_id,
        },
        "news": [{
            "headline": n.headline, "summary": n.summary,
            "published_date": n.published_date.isoformat(),
            "source_ref": n.url or n.source_record_id,
            "source_name": n.source_name,
        } for n in dated[:8]],
        "news_error": news_error,
        "source_refs": [latest.source_record_id or latest.source] + [
            n.url or n.source_record_id for n in dated[:8]
        ],
    }


def analyze(ticker: str, output: Path, deepseek: OllamaClient, senior: OpenClawStructuredClient) -> dict:
    path = output / f"{ticker}.json"
    row = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"ticker": ticker}
    if "evidence" not in row:
        try:
            row["evidence"] = evidence_for(ticker)
            row.pop("evidence_error", None)
        except Exception as exc:
            row["evidence_error"] = f"{type(exc).__name__}: {exc}"
            save(path, row)
            return row
        save(path, row)
    facts = row["evidence"]
    payload = json.dumps(facts, ensure_ascii=False)
    instructions = (
        "Analise apenas os fatos e fontes fornecidos. Separe cotação observada de notícia. "
        "Não invente fundamentos, preço alvo, ranking, probabilidade ou recomendação. "
        "Diga quando faltam notícias ou dados. Cite somente source_refs fornecidos."
    )
    if row.get("deepseek_status") != "completed":
        try:
            result = deepseek.ask(instructions + "\nEvidências:\n" + payload)
            row["deepseek"] = {"model": result.model, "analysis": result.content,
                               "eval_count": result.eval_count, "total_duration_ns": result.total_duration_ns}
            row["deepseek_status"] = "completed"
            row.pop("deepseek_error", None)
        except Exception as exc:
            row["deepseek_status"] = "failed"
            row["deepseek_error"] = f"{type(exc).__name__}: {exc}"
        save(path, row)
    if row.get("openclaw_status") != "completed":
        try:
            response = senior.complete_json(
                instructions=instructions, input_text=payload,
                schema_name="b3_ticker_research_v1", schema=SCHEMA,
            )
            if not isinstance(response, dict) or any(key not in response for key in SCHEMA["required"]):
                raise ValueError("Incomplete senior analysis schema")
            if not set(response["evidence_refs"]).issubset(set(facts["source_refs"])):
                raise ValueError("Senior analysis referenced unknown sources")
            row["openclaw"] = {"model": settings.openclaw_model, "analysis": response}
            row["openclaw_status"] = "completed"
            row.pop("openclaw_error", None)
        except Exception as exc:
            row["openclaw_status"] = "failed"
            row["openclaw_error"] = f"{type(exc).__name__}: {exc}"
        save(path, row)
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, choices=range(1, 21), metavar="1-20")
    args = parser.parse_args()
    output = settings.data_dir / "derived" / "intelligence_pilot_20"
    deepseek = OllamaClient()
    senior = OpenClawStructuredClient(agent=settings.openclaw_agent, model=settings.openclaw_model,
                                      timeout=settings.openclaw_timeout_seconds, executable=settings.openclaw_bin)
    rows = []
    for ticker in TICKERS[:args.limit]:
        row = analyze(ticker, output, deepseek, senior)
        rows.append({"ticker": ticker, "deepseek": row.get("deepseek_status", "not_run"),
                     "openclaw": row.get("openclaw_status", "not_run"),
                     "evidence_error": row.get("evidence_error")})
        manifest = {"as_of": datetime.now(timezone.utc).isoformat(), "requested": args.limit,
                    "both_completed": sum(r["deepseek"] == r["openclaw"] == "completed" for r in rows),
                    "results": rows}
        save(output / "latest.json", manifest)
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    return 0 if manifest["both_completed"] == args.limit else 2


if __name__ == "__main__":
    raise SystemExit(main())
