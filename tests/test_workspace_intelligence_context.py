from __future__ import annotations

from datetime import datetime, timezone

from b3_agent.intelligence import workspace_context
from b3_agent.intelligence.workspace_context import WorkspaceIntelligenceContextService
from b3_agent.schemas.macro import MacroObservation
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.news import NewsEvidence


NOW = datetime(2026, 10, 1, 16, 0, tzinfo=timezone.utc)


class FakeCurrentQuoteProvider:
    name = "oplab"

    def get_current_quote(self, ticker: str):
        return StockMarketData(
            instrument_id=ticker,
            ticker=ticker,
            observation_timestamp=NOW,
            available_timestamp=NOW,
            source="oplab",
            ingested_at=NOW,
            source_record_id=f"{ticker}:current",
            quality_flags=("current_quote",),
            open=49.0,
            high=50.0,
            low=48.5,
            close=49.4,
            volume=2_000_000,
            currency="BRL",
        )


class FakeNewsProvider:
    def search(self, ticker: str, *, query: str | None = None, limit: int = 20):
        return (
            NewsEvidence(
                instrument_id=ticker,
                ticker=ticker,
                observation_timestamp=NOW,
                available_timestamp=NOW,
                source="searxng",
                ingested_at=NOW,
                source_record_id=f"{ticker}:news:1",
                headline=f"{ticker} atualiza guidance",
                source_name="example",
                url=f"https://example.test/{ticker}",
                published_date=NOW.date(),
                published_at=NOW,
                event_type="NEWS",
                summary="Guidance atualizado pela companhia.",
            ),
        )


class FakeMacroRepository:
    def latest(self, indicator: str):
        return MacroObservation(
            instrument_id=indicator,
            ticker=indicator,
            observation_timestamp=NOW,
            available_timestamp=NOW,
            source="bcb_sgs",
            ingested_at=NOW,
            source_record_id=f"{indicator}:current",
            indicator=indicator,
            value={"SELIC": 12.0, "CDI": 11.9, "IPCA": 4.2}[indicator],
            unit="percent_per_year",
            reference_period="2026-10-01",
        )


class FakeJoao:
    def analyze(self, payload):
        assert payload["workspace"] == "Strategy Lab"
        assert payload["tickers"] == ["VALE3", "WEGE3"]
        return {
            "summary": "Perspectiva de pesquisa João.",
            "market_observations": ["Evento recente merece acompanhamento."],
            "risks": ["Evidência ainda limitada."],
            "contradictions": [],
            "questions_for_b3": ["Como isso altera o risco da estratégia?"],
            "source_refs": ["https://example.test/VALE3"],
        }


class FailingJoao:
    def analyze(self, payload):
        raise RuntimeError("joao unavailable")


def _ready_local(ticker: str):
    return {
        "ticker": ticker,
        "dossier": {
            "status": "READY",
            "quality_flags": [],
            "created_at": NOW.isoformat(),
            "model": "deepseek-r1:8b",
            "evidence_refs": [f"cvm:{ticker}:1"],
            "analysis": {
                "summary": f"Dossier local {ticker}",
                "risks": [],
                "catalysts": [],
                "contradictions": [],
                "questions_for_senior_review": [],
                "escalation_recommended": False,
                "evidence_refs": [f"cvm:{ticker}:1"],
            },
        },
        "relevance": None,
    }


def test_workspace_context_combines_market_macro_local_and_joao(monkeypatch):
    monkeypatch.setattr(workspace_context, "local_ticker_intelligence", _ready_local)
    service = WorkspaceIntelligenceContextService(
        current_quote_provider=FakeCurrentQuoteProvider(),
        news_provider=FakeNewsProvider(),
        macro_repository=FakeMacroRepository(),
        joao_service=FakeJoao(),
    )

    result = service.build(
        workspace="Strategy Lab",
        tickers=("VALE3", "WEGE3"),
        deterministic_result={"fast_route": {"target": "strategy_engine"}},
    )

    assert result.deterministic_context["workspace_result"]["fast_route"]["target"] == "strategy_engine"
    market = result.deterministic_context["market_analysis"]
    assert market["tickers"]["WEGE3"]["current_quote"]["close"] == 49.4
    assert market["tickers"]["VALE3"]["research_events"][0]["headline"].startswith("VALE3")
    assert market["macro"]["SELIC"]["value"] == 12.0

    local = result.derived_intelligence["b3_local_evidence_analyst"]
    assert local["VALE3"]["status"] == "READY"
    assert local["VALE3"]["analysis"]["summary"] == "Dossier local VALE3"

    joao = result.derived_intelligence["joao_resolve"]
    assert joao["status"] == "READY"
    assert joao["authority"] == "derived_non_authoritative"
    assert joao["summary"] == "Perspectiva de pesquisa João."
    assert "oplab" in result.source_refs
    assert "bcb_sgs" in result.source_refs


def test_workspace_context_omits_degraded_local_and_fails_soft_on_joao(monkeypatch):
    monkeypatch.setattr(
        workspace_context,
        "local_ticker_intelligence",
        lambda ticker: {
            "ticker": ticker,
            "dossier": {
                "status": "DEGRADED",
                "quality_flags": ["INVALID_JSON"],
                "analysis": {"summary": "must not enter senior context"},
            },
            "relevance": None,
        },
    )
    service = WorkspaceIntelligenceContextService(
        current_quote_provider=FakeCurrentQuoteProvider(),
        news_provider=FakeNewsProvider(),
        macro_repository=FakeMacroRepository(),
        joao_service=FailingJoao(),
    )

    result = service.build(
        workspace="Opportunities",
        tickers=("WEGE3",),
        deterministic_result={},
    )

    local = result.derived_intelligence["b3_local_evidence_analyst"]["WEGE3"]
    assert local["status"] == "OMITTED"
    assert local["quality_flags"] == ["INVALID_JSON"]
    assert "analysis" not in local

    joao = result.derived_intelligence["joao_resolve"]
    assert joao["status"] == "UNAVAILABLE"
    assert any("João Resolve perspective unavailable" in item for item in result.limitations)
