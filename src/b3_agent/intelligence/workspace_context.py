from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from typing import Any

from b3_agent.config import settings
from b3_agent.intelligence.observability import local_ticker_intelligence
from b3_agent.llm.client import OpenClawStructuredClient
from b3_agent.providers.oplab.adapter import OplabAdapter
from b3_agent.providers.searxng_news import SearxngNewsAdapter
from b3_agent.repositories.macro import MacroDataRepository
from b3_agent.research_events import ResearchEventService


JOAO_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "market_observations": {
            "type": "array",
            "items": {"type": "string"},
        },
        "risks": {"type": "array", "items": {"type": "string"}},
        "contradictions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "questions_for_b3": {
            "type": "array",
            "items": {"type": "string"},
        },
        "source_refs": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "summary",
        "market_observations",
        "risks",
        "contradictions",
        "questions_for_b3",
        "source_refs",
    ],
}


@dataclass(frozen=True)
class WorkspaceIntelligenceContext:
    workspace: str
    as_of: datetime
    tickers: tuple[str, ...]
    deterministic_context: dict[str, Any]
    derived_intelligence: dict[str, Any]
    source_refs: tuple[str, ...]
    limitations: tuple[str, ...]

    def as_context(self) -> dict[str, Any]:
        return {
            "workspace_intelligence": True,
            "deterministic_context": self.deterministic_context,
            "derived_intelligence": self.derived_intelligence,
            "workspace_intelligence_meta": {
                "workspace": self.workspace,
                "as_of": self.as_of.isoformat(),
                "tickers": list(self.tickers),
                "source_refs": list(self.source_refs),
                "limitations": list(self.limitations),
            },
        }


class JoaoResolvePerspectiveService:
    """Optional, non-authoritative João Resolve perspective.

    João receives only the bounded B3/market context supplied by this service.
    It never receives direct access to B3 canonical stores and cannot mutate
    deterministic facts or rankings.
    """

    def __init__(self, client: OpenClawStructuredClient | None = None) -> None:
        self.client = client or OpenClawStructuredClient(
            agent=os.getenv("B3_JOAO_OPENCLAW_AGENT", "joao-resolve"),
            model=os.getenv("B3_JOAO_OPENCLAW_MODEL", settings.openclaw_model),
            timeout=float(
                os.getenv(
                    "B3_JOAO_OPENCLAW_TIMEOUT_SECONDS",
                    str(min(settings.openclaw_timeout_seconds, 45.0)),
                )
            ),
            executable=settings.openclaw_bin,
        )

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.client.complete_json(
            instructions=(
                "Act as the João Resolve research perspective for the B3 "
                "investment copilot. Analyze only the supplied B3 deterministic "
                "facts, supplied market evidence and supplied derived B3 context. "
                "Do not invent prices, calculations, rankings, probabilities or "
                "causal claims. Do not override B3 deterministic authority. "
                "Identify useful market observations, risks, contradictions and "
                "questions that the B3 specialists should consider. Every factual "
                "claim must be traceable to supplied source_refs."
            ),
            input_text=json.dumps(
                payload,
                ensure_ascii=False,
                default=str,
            ),
            schema_name="joao_resolve_b3_perspective",
            schema=JOAO_SCHEMA,
        )
        supplied_refs = {
            str(item)
            for item in payload.get("source_refs") or ()
            if str(item).strip()
        }
        returned_refs = {
            str(item)
            for item in result.get("source_refs") or ()
            if str(item).strip()
        }
        unknown_refs = returned_refs - supplied_refs
        if unknown_refs:
            raise RuntimeError(
                "João Resolve referenced sources outside the supplied evidence: "
                + ", ".join(sorted(unknown_refs))
            )
        return result


class WorkspaceIntelligenceContextService:
    """Compose bounded intelligence context for Opportunities/Market/Strategy.

    The service does not produce canonical investment facts. It packages current
    provider observations, recent research evidence, current macro observations,
    accepted local B3 dossiers and an optional João Resolve perspective for the
    existing senior B3 workflow.
    """

    SUPPORTED_WORKSPACES = {
        "opportunities",
        "market intelligence",
        "strategy lab",
    }

    def __init__(
        self,
        *,
        current_quote_provider: OplabAdapter | None = None,
        news_provider: SearxngNewsAdapter | None = None,
        macro_repository: MacroDataRepository | None = None,
        joao_service: JoaoResolvePerspectiveService | None = None,
    ) -> None:
        self.current_quote_provider = current_quote_provider or OplabAdapter()
        self.news_provider = news_provider or SearxngNewsAdapter(
            base_url=os.getenv("B3_SEARXNG_URL", "http://127.0.0.1:8080")
        )
        self.macro_repository = macro_repository or MacroDataRepository(
            settings.data_dir / "normalized" / "macro"
        )
        self.joao_service = joao_service

    def build(
        self,
        *,
        workspace: str,
        tickers: tuple[str, ...] = (),
        deterministic_result: dict[str, Any] | None = None,
        include_joao: bool = True,
        news_limit: int = 8,
    ) -> WorkspaceIntelligenceContext:
        normalized_workspace = " ".join(workspace.casefold().split())
        if normalized_workspace not in self.SUPPORTED_WORKSPACES:
            raise ValueError(
                f"workspace intelligence is unsupported for {workspace!r}"
            )

        normalized_tickers = tuple(
            dict.fromkeys(
                ticker.upper().strip()
                for ticker in tickers
                if ticker and ticker.strip()
            )
        )
        as_of = datetime.now(timezone.utc)
        limitations: list[str] = []
        source_refs: list[str] = []

        market_by_ticker: dict[str, Any] = {}
        local_by_ticker: dict[str, Any] = {}
        for ticker in normalized_tickers:
            market_entry: dict[str, Any] = {}
            try:
                quote = self.current_quote_provider.get_current_quote(ticker)
                market_entry["current_quote"] = asdict(quote)
                source_refs.append(quote.source)
            except (OSError, RuntimeError, ValueError) as exc:
                market_entry["current_quote"] = None
                limitations.append(
                    f"Current OPLAB quote unavailable for {ticker}: {exc}"
                )

            try:
                records = self.news_provider.search(
                    ticker,
                    query=(
                        f"{ticker} B3 resultados fato relevante dividendos "
                        "mercado setor"
                    ),
                    limit=news_limit,
                )
                research = ResearchEventService().build(records, as_of=as_of)
                events = [asdict(item) for item in research.events]
                market_entry["research_events"] = events
                source_refs.extend(research.source_refs)
            except (OSError, RuntimeError, ValueError) as exc:
                market_entry["research_events"] = []
                limitations.append(
                    f"Current research/news unavailable for {ticker}: {exc}"
                )

            market_by_ticker[ticker] = market_entry

            local = local_ticker_intelligence(ticker)
            dossier = local.get("dossier")
            if (
                isinstance(dossier, dict)
                and dossier.get("status") == "READY"
                and not dossier.get("quality_flags")
                and isinstance(dossier.get("analysis"), dict)
            ):
                local_by_ticker[ticker] = {
                    "status": "READY",
                    "analysis": dossier["analysis"],
                    "created_at": dossier.get("created_at"),
                    "model": dossier.get("model"),
                    "evidence_refs": dossier.get("evidence_refs") or [],
                }
                source_refs.extend(
                    str(item)
                    for item in dossier.get("evidence_refs") or ()
                    if str(item).strip()
                )
            else:
                local_by_ticker[ticker] = {
                    "status": "OMITTED" if dossier else "ABSENT",
                    "quality_flags": (
                        list(dossier.get("quality_flags") or ())
                        if isinstance(dossier, dict)
                        else []
                    ),
                }

        market_overview_research: list[dict[str, Any]] = []
        if normalized_workspace in {"market intelligence", "opportunities"}:
            try:
                overview_records = self.news_provider.search(
                    "IBOV",
                    query=(
                        "Ibovespa B3 Brasil mercado juros Selic dólar inflação "
                        "commodities fluxo estrangeiro resultados empresas"
                    ),
                    limit=news_limit,
                )
                overview = ResearchEventService().build(
                    overview_records,
                    as_of=as_of,
                )
                market_overview_research = [
                    asdict(item) for item in overview.events
                ]
                source_refs.extend(overview.source_refs)
            except (OSError, RuntimeError, ValueError) as exc:
                limitations.append(
                    f"Current broad-market research unavailable: {exc}"
                )

        macro: dict[str, Any] = {}
        for indicator in ("SELIC", "CDI", "IPCA"):
            try:
                item = self.macro_repository.latest(indicator)
            except (OSError, RuntimeError, ValueError) as exc:
                limitations.append(
                    f"Macro repository unavailable for {indicator}: {exc}"
                )
                item = None
            if item is not None:
                macro[indicator] = asdict(item)
                source_refs.append(item.source)

        if (
            normalized_workspace == "opportunities"
            and not deterministic_result
        ):
            limitations.append(
                "No canonical UC-03 OpportunitySet was supplied for this request; "
                "B3/João intelligence may interpret market evidence but must not "
                "invent or rank stock opportunities without validated valuation "
                "and opportunity inputs."
            )

        deterministic_context: dict[str, Any] = {
            "workspace": workspace,
            "workspace_result": dict(deterministic_result or {}),
            "market_analysis": {
                "as_of": as_of.isoformat(),
                "tickers": market_by_ticker,
                "macro": macro,
                "market_overview_research": market_overview_research,
                "authority": (
                    "provider/evidence facts only; interpretation belongs to agents"
                ),
            },
        }

        derived_intelligence: dict[str, Any] = {
            "b3_local_evidence_analyst": local_by_ticker,
        }

        if include_joao:
            try:
                joao = (self.joao_service or JoaoResolvePerspectiveService()).analyze(
                    {
                        "workspace": workspace,
                        "as_of": as_of.isoformat(),
                        "tickers": list(normalized_tickers),
                        "deterministic_context": deterministic_context,
                        "b3_local_intelligence": local_by_ticker,
                        "source_refs": list(dict.fromkeys(source_refs)),
                    }
                )
                derived_intelligence["joao_resolve"] = {
                    "status": "READY",
                    "authority": "derived_non_authoritative",
                    **joao,
                }
                source_refs.extend(
                    str(item)
                    for item in joao.get("source_refs") or ()
                    if str(item).strip()
                )
            except (OSError, RuntimeError, ValueError) as exc:
                derived_intelligence["joao_resolve"] = {
                    "status": "UNAVAILABLE",
                    "authority": "derived_non_authoritative",
                    "error": str(exc),
                }
                limitations.append(
                    f"João Resolve perspective unavailable: {exc}"
                )

        return WorkspaceIntelligenceContext(
            workspace=workspace,
            as_of=as_of,
            tickers=normalized_tickers,
            deterministic_context=deterministic_context,
            derived_intelligence=derived_intelligence,
            source_refs=tuple(dict.fromkeys(source_refs)),
            limitations=tuple(dict.fromkeys(limitations)),
        )


__all__ = [
    "JoaoResolvePerspectiveService",
    "WorkspaceIntelligenceContext",
    "WorkspaceIntelligenceContextService",
]
