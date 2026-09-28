from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from b3_agent.config import settings
from b3_agent.llm.ollama_client import OllamaClient
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.providers.searxng_news import SearxngNewsAdapter
from b3_agent.research_events import ResearchEventService


def portfolio_tickers() -> list[str]:
    snapshots = load_active_snapshots(settings.data_dir)
    portfolio = snapshots.get("portfolio_context")
    if portfolio is None:
        return []
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
    return tickers


def _event_payload(event: Any) -> dict[str, Any]:
    return {
        "ticker": event.ticker,
        "event_type": event.event_type,
        "published_at": event.published_at.isoformat(),
        "headline": event.headline,
        "summary": event.summary,
        "source_name": event.source_name,
        "source_ref": event.source_ref,
    }


def _prompt(ticker: str, events: list[dict[str, Any]]) -> str:
    return (
        "You are the B3 local background analyst. Analyze only supplied evidence. "
        "Do not invent prices, facts, recommendations, probabilities or causal claims. "
        "Return concise sections: Summary; Material events; Risks; Catalysts; "
        "Contradictions; Escalation needed. "
        f"Ticker: {ticker}\nEvidence JSON:\n"
        + json.dumps(events, ensure_ascii=False)
    )


class NightlyIntelligenceJob:
    def __init__(self, *, news_limit: int = 8, output_dir: str | Path | None = None) -> None:
        self.news_limit = news_limit
        self.output_dir = Path(output_dir or settings.data_dir / "derived" / "nightly_intelligence")
        self.news = SearxngNewsAdapter(
            base_url=os.getenv("B3_SEARXNG_URL", "http://127.0.0.1:8080")
        )
        self.llm = OllamaClient()

    def run(self, *, tickers: list[str] | None = None) -> dict[str, Any]:
        selected = tickers or portfolio_tickers()
        if not selected:
            raise RuntimeError("no portfolio tickers available for nightly intelligence")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        as_of = datetime.now(timezone.utc)
        results: list[dict[str, Any]] = []

        for ticker in selected:
            records = self.news.search(ticker, limit=self.news_limit)
            snapshot = ResearchEventService().build(records, as_of=as_of)
            events = [_event_payload(event) for event in snapshot.events]
            if not events:
                results.append({"ticker": ticker, "status": "no_events", "event_count": 0})
                continue

            llm_result = self.llm.ask(_prompt(ticker, events))
            item = {
                "ticker": ticker,
                "status": "completed",
                "as_of": as_of.isoformat(),
                "event_count": len(events),
                "source_refs": list(snapshot.source_refs),
                "model": llm_result.model,
                "analysis": llm_result.content,
                "thinking_chars": len(llm_result.thinking),
                "total_duration_ns": llm_result.total_duration_ns,
                "eval_count": llm_result.eval_count,
                "eval_duration_ns": llm_result.eval_duration_ns,
            }
            results.append(item)
            (self.output_dir / f"{ticker}.json").write_text(
                json.dumps(item, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        manifest = {
            "as_of": as_of.isoformat(),
            "ticker_count": len(selected),
            "completed": sum(1 for item in results if item["status"] == "completed"),
            "results": results,
        }
        (self.output_dir / "latest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest
