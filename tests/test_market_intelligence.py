from __future__ import annotations

import json

from b3_agent.agents.market_intelligence import (
    MarketIntelligenceAgent,
    MARKET_INTELLIGENCE_SCOPE,
)


class FakeResearcher:
    def __init__(self) -> None:
        self.instructions = ""
        self.input_text = ""

    def research_json(self, *, instructions, input_text, schema_name, schema):
        self.instructions = instructions
        self.input_text = input_text
        assert schema_name == "market_intelligence"
        assert schema["additionalProperties"] is False
        return {
            "summary": "Macro and geopolitical developments are relevant to the portfolio.",
            "findings": ["A current event may affect the sector."],
            "macro_factors": ["Interest rates and USD/BRL"],
            "geopolitical_factors": ["A current conflict affecting commodities"],
            "climate_factors": ["A weather event affecting supply"],
            "sector_factors": ["Sector-specific regulation"],
            "risks": ["Source uncertainty"],
            "uncertainties": ["Impact magnitude is not established."],
            "evidence": [
                {
                    "title": "Authoritative market event",
                    "url": "https://example.com/event",
                    "published_at": "2026-09-17T08:00:00Z",
                    "retrieved_at": "2026-09-17T10:00:00Z",
                    "publisher": "Example Source",
                    "topic": "macro",
                    "relevance": "high",
                    "summary": "Current event with an identifiable market connection.",
                    "affected_tickers": ["petr4", " VALE3 "],
                }
            ],
            "source_refs": ["https://example.com/event"],
        }


def test_market_intelligence_search_scope_is_broad_and_investment_relevant():
    researcher = FakeResearcher()
    agent = MarketIntelligenceAgent(researcher)

    insight = agent.analyze(
        request="Assess current context for my portfolio",
        as_of="2026-09-17T10:00:00Z",
        tickers=("petr4", "PETR4", "vale3"),
        deterministic_context={"price": 100.0},
        portfolio_context={"positions": ["PETR4", "VALE3"]},
    )

    payload = json.loads(researcher.input_text)
    assert payload["tickers"] == ["PETR4", "VALE3"]
    assert "inflation" in payload["research_scope"].lower()
    assert "interest" in payload["research_scope"].lower()
    assert "usd/brl" in payload["research_scope"].lower()
    assert "wars" in payload["research_scope"].lower()
    assert "climate" in payload["research_scope"].lower()
    assert "capital flows" in payload["research_scope"].lower()
    assert insight.evidence[0].affected_tickers == ("PETR4", "VALE3")


def test_market_intelligence_preserves_point_in_time_and_sources():
    researcher = FakeResearcher()
    agent = MarketIntelligenceAgent(researcher)

    insight = agent.analyze(
        request="Research relevant events",
        as_of="2026-09-17T10:00:00Z",
        tickers=("ITUB4",),
    )

    assert insight.as_of == "2026-09-17T10:00:00Z"
    assert insight.evidence[0].url == "https://example.com/event"
    assert insight.evidence[0].published_at == "2026-09-17T08:00:00Z"
    assert insight.source_refs == ("https://example.com/event",)
    assert "only include information that was available" in researcher.instructions.lower()


def test_scope_is_not_stock_only():
    scope = MARKET_INTELLIGENCE_SCOPE.lower()
    for topic in ("inflation", "interest rates", "usd/brl", "commodities", "geopolitical", "climate/weather", "capital flows"):
        assert topic in scope
