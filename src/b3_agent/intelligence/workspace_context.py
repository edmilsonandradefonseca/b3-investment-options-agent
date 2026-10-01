from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
import urllib.request
from typing import Any

from b3_agent.config import settings
from b3_agent.intelligence.observability import local_ticker_intelligence
from b3_agent.llm.client import OpenClawStructuredClient
from b3_agent.opportunity_live import LiveOpportunityService
from b3_agent.providers.google_news_rss import GoogleNewsRssAdapter
from b3_agent.providers.oplab.adapter import OplabAdapter
from b3_agent.providers.searxng_news import SearxngNewsAdapter
from b3_agent.repositories.macro import MacroDataRepository
from b3_agent.research_events import ResearchEventService
from b3_agent.strategy_live import StrategyEvidenceService


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


class JoaoMemoryContextClient:
    """Read-only boundary to João Resolve's memory service.

    This client never accesses João's SQLite/Qdrant/Neo4j directly. It consumes
    only the existing HTTP context API and returns a bounded, non-authoritative
    context for B3 reasoning.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv(
                "B3_JOAO_MEMORY_URL",
                "http://127.0.0.1:8091",
            )
        ).rstrip("/")
        self.timeout = timeout

    def context(
        self,
        query: str,
        *,
        memory_limit: int = 5,
        relation_limit: int = 10,
    ) -> dict[str, Any]:
        normalized = " ".join(query.split()).strip()
        if not normalized:
            raise ValueError("João memory query must not be empty")
        payload = json.dumps(
            {
                "query": normalized,
                "memory_limit": max(1, min(memory_limit, 10)),
                "relation_limit": max(1, min(relation_limit, 20)),
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/context",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(
            request,
            timeout=self.timeout,
        ) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not isinstance(result, dict):
            raise ValueError("João memory context returned a non-object")
        raw_memories = result.get("memories")
        raw_relations = result.get("relations")
        memories: list[dict[str, Any]] = []
        source_refs: list[str] = []
        if isinstance(raw_memories, list):
            for item in raw_memories[:10]:
                if not isinstance(item, dict):
                    continue
                memory_id = str(item.get("id") or "").strip()
                source_ref = (
                    f"joao-memory:{memory_id}"
                    if memory_id
                    else "joao-memory-api"
                )
                source_refs.append(source_ref)
                memories.append(
                    {
                        "source_ref": source_ref,
                        "content": str(item.get("content") or ""),
                        "memory_type": item.get("memory_type"),
                        "source": item.get("source"),
                        "importance": item.get("importance"),
                        "score": item.get("score"),
                        "created_at": item.get("created_at"),
                    }
                )

        relations: list[dict[str, Any]] = []
        if isinstance(raw_relations, list):
            for item in raw_relations[:20]:
                if not isinstance(item, dict):
                    continue
                relations.append(
                    {
                        key: item.get(key)
                        for key in (
                            "source_entity",
                            "relation",
                            "id",
                            "name",
                        )
                        if item.get(key) is not None
                    }
                )

        return {
            "query": str(result.get("query") or normalized),
            "memories": memories,
            "relations": relations,
            "authority": "derived_non_authoritative",
            "source": "joao-memory-api",
            "source_refs": list(dict.fromkeys(source_refs)),
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
        fallback_news_provider: GoogleNewsRssAdapter | None = None,
        macro_repository: MacroDataRepository | None = None,
        asset_evidence_service: StrategyEvidenceService | None = None,
        joao_memory_client: JoaoMemoryContextClient | None = None,
        joao_service: JoaoResolvePerspectiveService | None = None,
        opportunity_service: LiveOpportunityService | None = None,
    ) -> None:
        self.current_quote_provider = current_quote_provider or OplabAdapter()
        self.news_provider = news_provider or SearxngNewsAdapter(
            base_url=os.getenv("B3_SEARXNG_URL", "http://127.0.0.1:8080")
        )
        self.fallback_news_provider = (
            fallback_news_provider or GoogleNewsRssAdapter()
        )
        self.macro_repository = macro_repository or MacroDataRepository(
            settings.data_dir / "normalized" / "macro"
        )
        self.asset_evidence_service = (
            asset_evidence_service or StrategyEvidenceService()
        )
        self.joao_memory_client = (
            joao_memory_client or JoaoMemoryContextClient()
        )
        self.joao_service = joao_service
        self.opportunity_service = opportunity_service or LiveOpportunityService()

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

        supplied_asset_evidence = {}
        if isinstance(deterministic_result, dict):
            candidate = deterministic_result.get("asset_evidence")
            if isinstance(candidate, dict):
                supplied_asset_evidence = candidate

        market_by_ticker: dict[str, Any] = {}
        local_by_ticker: dict[str, Any] = {}
        for ticker in normalized_tickers:
            market_entry: dict[str, Any] = {}
            supplied_pack = supplied_asset_evidence.get(ticker)
            if isinstance(supplied_pack, dict):
                market_entry["asset_evidence"] = supplied_pack
                supplied_market = supplied_pack.get("market")
                if isinstance(supplied_market, dict):
                    market_entry["current_quote"] = supplied_market.get(
                        "current_quote"
                    )
                for source in supplied_pack.get("source_refs") or ():
                    if str(source).strip():
                        source_refs.append(str(source))
            else:
                try:
                    pack = self.asset_evidence_service.build(
                        ticker,
                        as_of=as_of,
                    )
                    packed = asdict(pack)
                    market_entry["asset_evidence"] = packed
                    market_entry["current_quote"] = packed.get(
                        "market", {}
                    ).get("current_quote")
                    source_refs.extend(pack.source_refs)
                except (OSError, RuntimeError, ValueError) as exc:
                    market_entry["asset_evidence"] = None
                    limitations.append(
                        f"Deterministic B3 asset evidence unavailable for "
                        f"{ticker}: {exc}"
                    )

            if market_entry.get("current_quote") is None:
                try:
                    quote = self.current_quote_provider.get_current_quote(ticker)
                    market_entry["current_quote"] = asdict(quote)
                    source_refs.append(quote.source)
                except (OSError, RuntimeError, ValueError) as exc:
                    market_entry["current_quote"] = None
                    limitations.append(
                        f"Current OPLAB quote unavailable for {ticker}: {exc}"
                    )

            ticker_query = (
                f"{ticker} B3 resultados fato relevante dividendos mercado setor"
            )
            ticker_events: list[dict[str, Any]] = []
            ticker_research_errors: list[str] = []
            try:
                records = self.news_provider.search(
                    ticker,
                    query=ticker_query,
                    limit=news_limit,
                )
                research = ResearchEventService().build(records, as_of=as_of)
                ticker_events = [asdict(item) for item in research.events]
                source_refs.extend(research.source_refs)
            except (OSError, RuntimeError, ValueError) as exc:
                ticker_research_errors.append(f"searxng={exc}")

            if not ticker_events:
                try:
                    fallback_records = self.fallback_news_provider.search(
                        ticker,
                        query=f"{ticker_query} when:2d",
                        limit=news_limit,
                    )
                    fallback_research = ResearchEventService().build(
                        fallback_records,
                        as_of=as_of,
                    )
                    ticker_events = [
                        asdict(item) for item in fallback_research.events
                    ]
                    source_refs.extend(fallback_research.source_refs)
                except (OSError, RuntimeError, ValueError) as exc:
                    ticker_research_errors.append(
                        f"google_news_rss={exc}"
                    )

            market_entry["research_events"] = ticker_events
            if not ticker_events and ticker_research_errors:
                limitations.append(
                    f"Current research/news unavailable for {ticker}: "
                    + "; ".join(ticker_research_errors)
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
        market_overview_diagnostics: list[dict[str, Any]] = []
        if normalized_workspace in {"market intelligence", "opportunities"}:
            overview_queries = (
                "Ibovespa B3 Brasil mercado hoje juros Selic dólar inflação commodities fluxo estrangeiro",
                "Ibovespa hoje bolsa brasileira dólar juros mercado",
                "B3 fluxo estrangeiro bolsa Brasil mercado hoje",
            )
            seen_refs: set[str] = set()
            for query in overview_queries:
                try:
                    overview_records = self.news_provider.search(
                        "IBOV",
                        query=query,
                        limit=news_limit,
                    )
                    diagnostics = getattr(
                        self.news_provider,
                        "last_diagnostics",
                        None,
                    )
                    if diagnostics is not None:
                        market_overview_diagnostics.append({
                            "query": diagnostics.query,
                            "primary_raw_result_count": diagnostics.primary_raw_result_count,
                            "fallback_raw_result_count": diagnostics.fallback_raw_result_count,
                            "normalized_result_count": diagnostics.normalized_result_count,
                            "fallback_used": diagnostics.fallback_used,
                            "fallback_strategy": diagnostics.fallback_strategy,
                            "unresponsive_engines": [
                                {"engine": name, "reason": reason}
                                for name, reason in diagnostics.unresponsive_engines
                            ],
                        })
                    overview = ResearchEventService().build(
                        overview_records,
                        as_of=as_of,
                    )
                    for item in overview.events:
                        if item.source_ref in seen_refs:
                            continue
                        seen_refs.add(item.source_ref)
                        market_overview_research.append(asdict(item))
                    source_refs.extend(overview.source_refs)
                    if len(market_overview_research) >= news_limit:
                        break
                except (OSError, RuntimeError, ValueError) as exc:
                    market_overview_diagnostics.append({
                        "query": query,
                        "error": str(exc),
                    })
            market_overview_research = market_overview_research[:news_limit]
            if not market_overview_research:
                fallback_query = (
                    "Ibovespa B3 Brasil mercado juros Selic dólar inflação "
                    "commodities fluxo estrangeiro when:1d"
                )
                try:
                    fallback_records = self.fallback_news_provider.search(
                        "IBOV",
                        query=fallback_query,
                        limit=news_limit,
                    )
                    fallback_snapshot = ResearchEventService().build(
                        fallback_records,
                        as_of=as_of,
                    )
                    market_overview_research = [
                        asdict(item)
                        for item in fallback_snapshot.events[:news_limit]
                    ]
                    source_refs.extend(fallback_snapshot.source_refs)
                    market_overview_diagnostics.append({
                        "query": fallback_query,
                        "source": self.fallback_news_provider.name,
                        "normalized_result_count": len(
                            market_overview_research
                        ),
                        "fallback_used": True,
                        "fallback_strategy": "google_news_rss",
                    })
                except (OSError, RuntimeError, ValueError) as exc:
                    market_overview_diagnostics.append({
                        "query": fallback_query,
                        "source": "google_news_rss",
                        "error": str(exc),
                    })

            if not market_overview_research:
                limitations.append(
                    "Broad-market research returned zero normalized events from "
                    "SearXNG and Google News RSS; macro and asset-specific evidence "
                    "remain available."
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

        workspace_result = dict(deterministic_result or {})
        if normalized_workspace == "opportunities" and normalized_tickers:
            if "opportunity_set" not in workspace_result:
                try:
                    live_opportunities = self.opportunity_service.build(
                        normalized_tickers[0],
                        as_of=as_of,
                        limit=20,
                    )
                    live_payload = self.opportunity_service.as_payload(
                        live_opportunities
                    )
                    workspace_result["opportunity_set"] = live_payload[
                        "opportunity_set"
                    ]
                    workspace_result["option_marketability"] = live_payload[
                        "option_marketability"
                    ]
                    workspace_result["opportunity_limitations"] = live_payload[
                        "limitations"
                    ]
                    source_refs.extend(
                        live_opportunities.opportunity_set.source_refs
                    )
                    limitations.extend(live_opportunities.limitations)
                except (OSError, RuntimeError, ValueError) as exc:
                    limitations.append(
                        "Canonical live option OpportunitySet unavailable for "
                        f"{normalized_tickers[0]}: {exc}"
                    )

        if (
            normalized_workspace == "opportunities"
            and "opportunity_set" not in workspace_result
        ):
            limitations.append(
                "No canonical UC-03 OpportunitySet is available. B3/João may "
                "interpret evidence but must not invent stock ranking or valuation."
            )

        deterministic_context: dict[str, Any] = {
            "workspace": workspace,
            "workspace_result": workspace_result,
            "market_analysis": {
                "as_of": as_of.isoformat(),
                "tickers": market_by_ticker,
                "macro": macro,
                "market_overview_research": market_overview_research,
                "market_overview_diagnostics": market_overview_diagnostics,
                "authority": (
                    "provider/evidence facts only; interpretation belongs to agents"
                ),
            },
        }

        derived_intelligence: dict[str, Any] = {
            "b3_local_evidence_analyst": local_by_ticker,
        }

        joao_memory_context: dict[str, Any] | None = None
        if include_joao:
            try:
                joao_memory_context = self.joao_memory_client.context(
                    " ".join(
                        [
                            "B3",
                            workspace,
                            *normalized_tickers,
                            "mercado oportunidades riscos evidências pesquisa",
                        ]
                    )
                )
                derived_intelligence["joao_memory_context"] = (
                    joao_memory_context
                )
                source_refs.append("joao-memory-api")
                source_refs.extend(
                    str(item)
                    for item in joao_memory_context.get("source_refs") or ()
                    if str(item).strip()
                )
            except (OSError, RuntimeError, ValueError) as exc:
                derived_intelligence["joao_memory_context"] = {
                    "status": "UNAVAILABLE",
                    "authority": "derived_non_authoritative",
                    "source": "joao-memory-api",
                    "error": str(exc),
                }
                limitations.append(
                    f"João Resolve memory context unavailable: {exc}"
                )

        if include_joao:
            try:
                joao = (self.joao_service or JoaoResolvePerspectiveService()).analyze(
                    {
                        "workspace": workspace,
                        "as_of": as_of.isoformat(),
                        "tickers": list(normalized_tickers),
                        "deterministic_context": deterministic_context,
                        "b3_local_intelligence": local_by_ticker,
                        "joao_memory_context": joao_memory_context,
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
    "JoaoMemoryContextClient",
    "JoaoResolvePerspectiveService",
    "WorkspaceIntelligenceContext",
    "WorkspaceIntelligenceContextService",
]
