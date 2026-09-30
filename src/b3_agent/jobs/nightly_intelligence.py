from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from b3_agent.config import settings
from b3_agent.intelligence import AcquisitionStatus, EvidenceConclusion
from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
from b3_agent.knowledge.evidence import Evidence
from b3_agent.llm.ollama_client import OllamaClient
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.providers.searxng_news import SearxngNewsAdapter
from b3_agent.research_events import ResearchEventService


_STATIC_DOMAINS = {
    "statusinvest.com.br",
    "www.statusinvest.com.br",
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
        "evidence_type": "open_web_event",
        "ticker": event.ticker,
        "event_type": event.event_type,
        "published_at": event.published_at.isoformat(),
        "headline": event.headline,
        "summary": event.summary,
        "source_name": event.source_name,
        "source_ref": event.source_ref,
    }


def _official_evidence_payload(evidence: Evidence) -> dict[str, Any]:
    metadata = evidence.metadata
    return {
        "evidence_type": "official_disclosure",
        "ticker_refs": list(metadata.ticker_refs),
        "issuer_ref": metadata.issuer_ref,
        "cvm_code": metadata.cvm_code,
        "published_at": (
            metadata.published_at.isoformat() if metadata.published_at else None
        ),
        "reference_at": (
            metadata.reference_at.isoformat() if metadata.reference_at else None
        ),
        "headline": evidence.title,
        "summary": evidence.content,
        "source_name": metadata.source,
        "source_ref": evidence.source_url or evidence.evidence_id,
        "materiality": metadata.materiality,
        "materiality_reason": metadata.materiality_reason,
        "pit_status": metadata.pit_status,
        "evidence_id": evidence.evidence_id,
    }


def _recent_official_evidence(
    evidences: tuple[Evidence, ...],
    *,
    as_of: datetime,
    days: int = 3,
) -> tuple[Evidence, ...]:
    cutoff = as_of - timedelta(days=days)
    selected: list[Evidence] = []
    for evidence in evidences:
        metadata = evidence.metadata
        timestamp = (
            metadata.published_at
            or metadata.observed_at
            or metadata.retrieved_at
        )
        if timestamp <= as_of and timestamp >= cutoff:
            selected.append(evidence)
    return tuple(selected)


def _looks_static(event: Any) -> bool:
    host = urlparse(event.source_ref).netloc.lower()
    title = (event.headline or "").lower()
    if host in _STATIC_DOMAINS:
        return True
    return any(term in title for term in _STATIC_TITLE_TERMS)


def _looks_material(event: Any) -> bool:
    text = f"{event.headline or ''} {event.summary or ''}".lower()
    return any(term in text for term in _MATERIAL_TERMS)


def _recent_dated_records(records: tuple[Any, ...], *, days: int = 3) -> tuple[Any, ...]:
    cutoff = date.today() - timedelta(days=days)
    return tuple(
        record
        for record in records
        if getattr(record, "published_date", None) is not None
        and record.published_date >= cutoff
    )


def _select_material_events(events: tuple[Any, ...]) -> list[Any]:
    selected: list[Any] = []
    seen: set[str] = set()
    for event in events:
        if _looks_static(event) or not _looks_material(event):
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
        "Every factual claim must be directly supported by supplied evidence. "
        "Do not infer price moves, causes, dates, amounts or events not literally present. "
        "Return concise sections: Summary; Material events; Risks; Catalysts; "
        "Contradictions; Escalation needed. "
        f"Ticker: {ticker}\nEvidence JSON:\n"
        + json.dumps(events, ensure_ascii=False)
    )


class NightlyIntelligenceJob:
    def __init__(
        self,
        *,
        news_limit: int = 8,
        max_deepseek_calls: int | None = None,
        output_dir: str | Path | None = None,
        local_analysis_mode: str = "inline",
        local_analysis_queue: LocalEvidenceQueue | None = None,
    ) -> None:
        self.news_limit = news_limit
        self.max_deepseek_calls = (
            max_deepseek_calls
            if max_deepseek_calls is not None
            else int(
                os.getenv(
                    "B3_NIGHTLY_MAX_LOCAL_ANALYSIS_ENQUEUES",
                    os.getenv("B3_NIGHTLY_MAX_DEEPSEEK_CALLS", "5"),
                )
            )
        )
        self.output_dir = Path(
            output_dir or settings.data_dir / "derived" / "nightly_intelligence"
        )
        if local_analysis_mode not in {"inline", "enqueue"}:
            raise ValueError("local_analysis_mode must be 'inline' or 'enqueue'")
        self.local_analysis_mode = local_analysis_mode
        self.local_analysis_queue = local_analysis_queue or LocalEvidenceQueue(
            settings.data_dir / "derived" / "local_evidence_analyst"
        )
        self.news = SearxngNewsAdapter(
            base_url=os.getenv("B3_SEARXNG_URL", "http://127.0.0.1:8080")
        )
        self.llm = OllamaClient()

    def run(
        self,
        *,
        tickers: list[str] | None = None,
        official_evidence_by_ticker: dict[str, tuple[Evidence, ...]] | None = None,
    ) -> dict[str, Any]:
        selected = tickers or portfolio_tickers()
        official_map = {
            key.upper().strip(): value
            for key, value in (official_evidence_by_ticker or {}).items()
        }
        if not selected:
            raise RuntimeError("no portfolio tickers available for nightly intelligence")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        run_started_at = datetime.now(timezone.utc)
        results: list[dict[str, Any]] = []
        deepseek_calls = 0
        local_analysis_enqueues = 0

        for ticker in selected:
            try:
                budget_used = (
                    deepseek_calls
                    if self.local_analysis_mode == "inline"
                    else local_analysis_enqueues
                )
                result = self._process_ticker(
                    ticker=ticker,
                    deepseek_allowed=budget_used < self.max_deepseek_calls,
                    official_evidence=official_map.get(ticker.upper().strip(), ()),
                )
                if result["status"] == "completed":
                    deepseek_calls += 1
                if (
                    result["status"] == "queued_local_analysis"
                    and result.get("local_analysis_queue_status") == "ENQUEUED"
                ):
                    local_analysis_enqueues += 1
                results.append(result)
            except Exception as exc:
                results.append({
                    "ticker": ticker,
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                })

        manifest = {
            "as_of": datetime.now(timezone.utc).isoformat(),
            "run_started_at": run_started_at.isoformat(),
            "ticker_count": len(selected),
            "completed": sum(1 for item in results if item["status"] == "completed"),
            "queued_local_analysis": sum(
                1 for item in results if item["status"] == "queued_local_analysis"
            ),
            "skipped": sum(1 for item in results if item["status"].startswith("skipped_")),
            "deferred": sum(
                1
                for item in results
                if item["status"] in {
                    "deferred_deepseek_budget",
                    "deferred_local_analysis_budget",
                }
            ),
            "coverage_insufficient": sum(
                1 for item in results if item["status"] == "coverage_insufficient"
            ),
            "failed": sum(1 for item in results if item["status"] == "failed"),
            "deepseek_calls": deepseek_calls,
            "local_analysis_enqueues": local_analysis_enqueues,
            "local_analysis_mode": self.local_analysis_mode,
            "max_deepseek_calls": self.max_deepseek_calls,
            "results": results,
        }
        (self.output_dir / "latest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest

    def _process_ticker(
        self,
        *,
        ticker: str,
        deepseek_allowed: bool,
        official_evidence: tuple[Evidence, ...] = (),
    ) -> dict[str, Any]:
        query = f"{ticker} notícias fato relevante resultados dividendos mercado"
        records = self.news.search(ticker, query=query, limit=self.news_limit)
        diagnostics = getattr(self.news, "last_diagnostics", None)
        recent_records = _recent_dated_records(records)
        dated_result_count = sum(
            1 for record in records if getattr(record, "published_date", None) is not None
        )
        snapshot_as_of = datetime.now(timezone.utc)
        snapshot = ResearchEventService().build(recent_records, as_of=snapshot_as_of)
        material_events = _select_material_events(snapshot.events)
        recent_official = _recent_official_evidence(
            official_evidence,
            as_of=snapshot_as_of,
        )
        official_material = tuple(
            item
            for item in recent_official
            if item.metadata.materiality == "MATERIAL"
        )
        official_candidates = tuple(
            item
            for item in recent_official
            if item.metadata.materiality == "CANDIDATE"
        )

        engine_errors = []
        fallback_used = False
        fallback_strategy = None
        primary_raw_result_count = len(records)
        fallback_raw_result_count = 0
        if diagnostics is not None:
            engine_errors = [
                {"engine": name, "reason": reason}
                for name, reason in diagnostics.unresponsive_engines
            ]
            fallback_used = diagnostics.fallback_used
            fallback_strategy = diagnostics.fallback_strategy
            primary_raw_result_count = diagnostics.primary_raw_result_count
            fallback_raw_result_count = diagnostics.fallback_raw_result_count

        if not records:
            acquisition_status = (
                AcquisitionStatus.DEGRADED
                if engine_errors
                else AcquisitionStatus.EMPTY
            )
        elif engine_errors:
            acquisition_status = AcquisitionStatus.PARTIAL
        else:
            acquisition_status = AcquisitionStatus.SUCCESS

        if material_events or official_material:
            evidence_conclusion = EvidenceConclusion.MATERIAL_FOUND
        elif not records or dated_result_count == 0:
            evidence_conclusion = EvidenceConclusion.COVERAGE_INSUFFICIENT
        else:
            evidence_conclusion = EvidenceConclusion.NO_MATERIAL_FOUND

        base = {
            "ticker": ticker,
            "as_of": snapshot_as_of.isoformat(),
            "raw_result_count": len(records),
            "primary_raw_result_count": primary_raw_result_count,
            "fallback_raw_result_count": fallback_raw_result_count,
            "dated_result_count": dated_result_count,
            "dated_recent_count": len(recent_records),
            "raw_event_count": len(snapshot.events),
            "material_event_count": len(material_events),
            "official_evidence_count": len(recent_official),
            "official_material_count": len(official_material),
            "official_candidate_count": len(official_candidates),
            "material_evidence_count": len(material_events) + len(official_material),
            "acquisition_status": acquisition_status.value,
            "evidence_conclusion": evidence_conclusion.value,
            "fallback_used": fallback_used,
            "fallback_strategy": fallback_strategy,
            "engine_errors": engine_errors,
        }

        if evidence_conclusion == EvidenceConclusion.COVERAGE_INSUFFICIENT:
            return {
                **base,
                "status": "coverage_insufficient",
            }

        if not material_events and not official_material:
            return {
                **base,
                "status": "skipped_no_material_events",
            }

        web_payloads = [_event_payload(event) for event in material_events]
        official_payloads = [
            _official_evidence_payload(evidence)
            for evidence in official_material
        ]
        events = web_payloads + official_payloads
        source_refs = [event["source_ref"] for event in events]

        if not deepseek_allowed:
            return {
                **base,
                "status": (
                    "deferred_local_analysis_budget"
                    if self.local_analysis_mode == "enqueue"
                    else "deferred_deepseek_budget"
                ),
                "source_refs": source_refs,
                "evidence_events": events,
            }

        if self.local_analysis_mode == "enqueue":
            queued = self.local_analysis_queue.enqueue(ticker, events)
            return {
                **base,
                "status": "queued_local_analysis",
                "source_refs": source_refs,
                "evidence_events": events,
                "local_analysis_id": queued.request.analysis_id,
                "local_analysis_fingerprint": queued.request.evidence_fingerprint,
                "local_analysis_queue_status": queued.queue_status,
            }

        llm_result = self.llm.ask(_prompt(ticker, events))
        item = {
            **base,
            "status": "completed",
            "source_refs": source_refs,
            "evidence_events": events,
            "prompt_version": "b3_uc10_canonical_evidence_v2",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "escalation_status": "pending_review",
            "model": llm_result.model,
            "analysis": llm_result.content,
            "thinking_chars": len(llm_result.thinking),
            "total_duration_ns": llm_result.total_duration_ns,
            "eval_count": llm_result.eval_count,
            "eval_duration_ns": llm_result.eval_duration_ns,
        }
        (self.output_dir / f"{ticker}.json").write_text(
            json.dumps(item, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return item
