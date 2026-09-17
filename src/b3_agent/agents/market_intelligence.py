from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from openai import OpenAI


MARKET_INTELLIGENCE_SCOPE = (
    "Analyze current information that can materially affect Brazilian investments. "
    "Cover the requested securities and their sectors, but also search beyond the "
    "securities themselves when relevant: Brazilian and global inflation, interest "
    "rates and central-bank decisions, fiscal policy, USD/BRL and major currencies, "
    "commodities such as oil/iron ore, global rates and risk appetite, China and other "
    "major economies, wars/geopolitical conflicts and sanctions, climate/weather and "
    "natural disasters, regulation, elections/policy only when economically relevant, "
    "capital flows, foreign investment, corporate actions, earnings, M&A, supply-chain "
    "events and sector-specific developments. Do not assume a topic is relevant; "
    "establish the causal connection to an instrument, sector, portfolio or market."
)


class WebResearchClient(Protocol):
    """LLM boundary for live web research with structured output."""

    def research_json(
        self,
        *,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]: ...


class OpenAIWebResearchClient:
    """OpenAI Responses adapter with the hosted web_search tool."""

    def __init__(self, *, model: str = "gpt-5.6-luna", client: OpenAI | None = None):
        self.model = model
        self.client = client or OpenAI()

    def research_json(
        self,
        *,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=input_text,
            tools=[{"type": "web_search"}],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        return json.loads(response.output_text)


@dataclass(frozen=True)
class MarketEvidence:
    """A point-in-time web fact retained with provenance."""

    title: str
    url: str
    published_at: str | None
    retrieved_at: str
    publisher: str | None
    topic: str
    relevance: str
    summary: str
    affected_tickers: tuple[str, ...] = ()


@dataclass(frozen=True)
class MarketInsight:
    """Structured market intelligence; it is not a final investment decision."""

    as_of: str
    summary: str
    findings: tuple[str, ...]
    macro_factors: tuple[str, ...]
    geopolitical_factors: tuple[str, ...]
    climate_factors: tuple[str, ...]
    sector_factors: tuple[str, ...]
    risks: tuple[str, ...]
    uncertainties: tuple[str, ...]
    evidence: tuple[MarketEvidence, ...]
    source_refs: tuple[str, ...]


class MarketIntelligenceAgent:
    """Researches live web information and relates it to investment context.

    The agent does not calculate market metrics, replace deterministic providers,
    rank opportunities, execute orders, or make the final investment decision.
    """

    agent_name = "market_intelligence"

    def __init__(self, researcher: WebResearchClient):
        self.researcher = researcher

    def analyze(
        self,
        *,
        request: str,
        as_of: str,
        tickers: tuple[str, ...] = (),
        deterministic_context: dict[str, Any] | None = None,
        portfolio_context: dict[str, Any] | None = None,
    ) -> MarketInsight:
        facts = deterministic_context or {}
        portfolio = portfolio_context or {}
        normalized_tickers = tuple(sorted({t.strip().upper() for t in tickers if t.strip()}))

        prompt = {
            "request": request,
            "as_of": as_of,
            "tickers": normalized_tickers,
            "deterministic_context": facts,
            "portfolio_context": portfolio,
            "research_scope": MARKET_INTELLIGENCE_SCOPE,
        }

        result = self.researcher.research_json(
            instructions=(
                "You are the Market Intelligence Agent for a Brazilian investment "
                "decision system. Use live web search for current information. "
                "Research first, then synthesize. Prefer primary/authoritative sources "
                "and reputable financial/news sources. Use multiple independent sources "
                "for material claims when practical. Never invent a source or URL. "
                "Preserve publication dates and distinguish facts from interpretation. "
                "Only include information that was available by the supplied as_of time. "
                "Explain the link between macro/geopolitical/climate/sector events and "
                "the affected instrument or portfolio. Do not calculate indicators, "
                "replace BRAPI/OpLab/BTG facts, rank opportunities, or make a final "
                "BUY/SELL/HOLD decision. Return concise, auditable evidence."
            ),
            input_text=json.dumps(prompt, ensure_ascii=False, default=str),
            schema_name="market_intelligence",
            schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "summary": {"type": "string"},
                    "findings": {"type": "array", "items": {"type": "string"}},
                    "macro_factors": {"type": "array", "items": {"type": "string"}},
                    "geopolitical_factors": {"type": "array", "items": {"type": "string"}},
                    "climate_factors": {"type": "array", "items": {"type": "string"}},
                    "sector_factors": {"type": "array", "items": {"type": "string"}},
                    "risks": {"type": "array", "items": {"type": "string"}},
                    "uncertainties": {"type": "array", "items": {"type": "string"}},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "title": {"type": "string"},
                                "url": {"type": "string"},
                                "published_at": {"type": ["string", "null"]},
                                "retrieved_at": {"type": "string"},
                                "publisher": {"type": ["string", "null"]},
                                "topic": {"type": "string"},
                                "relevance": {"type": "string"},
                                "summary": {"type": "string"},
                                "affected_tickers": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": [
                                "title", "url", "published_at", "retrieved_at", "publisher",
                                "topic", "relevance", "summary", "affected_tickers"
                            ],
                        },
                    },
                    "source_refs": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "summary", "findings", "macro_factors", "geopolitical_factors",
                    "climate_factors", "sector_factors", "risks", "uncertainties",
                    "evidence", "source_refs"
                ],
            },
        )

        evidence = tuple(
            MarketEvidence(
                title=item["title"],
                url=item["url"],
                published_at=item["published_at"],
                retrieved_at=item["retrieved_at"],
                publisher=item["publisher"],
                topic=item["topic"],
                relevance=item["relevance"],
                summary=item["summary"],
                affected_tickers=tuple(
                    sorted({t.strip().upper() for t in item["affected_tickers"] if t.strip()})
                ),
            )
            for item in result["evidence"]
        )

        return MarketInsight(
            as_of=as_of,
            summary=result["summary"],
            findings=tuple(result["findings"]),
            macro_factors=tuple(result["macro_factors"]),
            geopolitical_factors=tuple(result["geopolitical_factors"]),
            climate_factors=tuple(result["climate_factors"]),
            sector_factors=tuple(result["sector_factors"]),
            risks=tuple(result["risks"]),
            uncertainties=tuple(result["uncertainties"]),
            evidence=evidence,
            source_refs=tuple(result["source_refs"]),
        )
