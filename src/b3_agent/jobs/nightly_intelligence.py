from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from b3_agent.config import settings
from b3_agent.llm.ollama_client import OllamaClient
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.providers.searxng_news import SearxngNewsAdapter
from b3_agent.research_events import ResearchEventService


_STATIC_DOMAINS = {
    "statusinvest.com.br",
    "www.statusinvest.com.br",
    "sistemaswebb3-listados.b3.com.br",
}
_STATIC_TITLE_TERMS = (
    "cotação",
    "cotacao",
    "ações ",
    "acoes ",
    "visão geral",
    "visao geral",
    "overview",
    "indicadores",
)
_MATERIAL_TERMS = (
    "resultado",
    "lucro",
    "prejuízo",
    "prejuizo",
    "ebitda",
    "receita",
    "guidance",
    "dividendo",
    "juros sobre capital",
    "jcp",
    "fato relevante",
    "comunicado ao mercado",
    "aquisição",
    "aquisicao",
    "venda de ativo",
    "desinvestimento",
    "capex",
    "produção",
    "producao",
    "reserva",
    "contrato",
    "parceria",
    "regulação",
    "regulacao",
    "processo",
    "multa",
    "governança",
    "governanca",
    "mudança de presidente",
    "mudanca de presidente",
    "ceo",
    "cfo",
)


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


def _looks_static(event: Any) -> bool:
    host = urlparse(event.source_ref).netloc.lower()
    title = (event.headline or "").lower()
    if host in _STATIC_DOMAINS:
        return True
    return any(term in title for term in _STATIC_TITLE_TERMS)


def _looks_material(event: Any) -> bool:
    text = f"{event.headline or ''} {event.summary or ''}".lower()
    return any(term in text for term in _MATERIAL_TERMS)


def _select_material_events(events: tuple[Any, ...]) -> list[Any]:
    selected: list[Any] = []
    seen: set[str] = set()
    for event in events:
        if _looks_static(event):
            continue
        if not _looks_material(event):
            continue
        key = " ".join((event.headline or "").lower().split())
        if key in seen:
            continue
        seen.add(key)
        selected.append(event)
    return selected[:3]


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
        run_started_at = datetime.now(timezone.utc)
        results: list[dict[str, Any]] = []

        for ticker in selected:
            query = f"{ticker} notícias fato relevante resultados dividendos mercado"
            records = self.news.search(ticker, query=query, limit=self.news_limit)
            snapshot_as_of = datetime.now(timezone.utc)
            snapshot = ResearchEventService().build(records, as_of=snapshot_as_of)
            material_events = _select_material_events(snapshot.events)
            if not material_events:
                results.append({
                    "ticker": ticker,
                    "status": "skipped_no_material_events",
                    "raw_event_count": len(snapshot.events),
                    "material_event_count": 0,
                })
                continue

            events = [_event_payload(event) for event in material_events]
            llm_result = self.llm.ask(_prompt(ticker, events))
            item = {
                "ticker": ticker,
                "status": "completed",
                "as_of": snapshot_as_of.isoformat(),
                "raw_event_count": len(snapshot.events),
                "material_event_count": len(events),
                "source_refs": [event["source_ref"] for event in events],
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
            "as_of": datetime.now(timezone.utc).isoformat(),
            "run_started_at": run_started_at.isoformat(),
            "ticker_count": len(selected),
            "completed": sum(1 for item in results if item["status"] == "completed"),
            "skipped": sum(1 for item in results if item["status"].startswith("skipped_")),
            "results": results,
        }
        (self.output_dir / "latest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest
