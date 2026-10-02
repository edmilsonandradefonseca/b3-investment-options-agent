from __future__ import annotations

from datetime import datetime, timezone
import pytest

from b3_agent.intelligence import workspace_context
from b3_agent.intelligence.workspace_context import JoaoMemoryContextClient, JoaoResolvePerspectiveService, WorkspaceIntelligenceContextService
from b3_agent.strategy_live import AssetEvidencePack
from b3_agent.schemas.macro import MacroObservation
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.news import NewsEvidence


@pytest.fixture(autouse=True)
def no_production_research_connections(monkeypatch):
    # Existing workspace tests isolate their provider inputs; memory is tested separately.
    monkeypatch.setattr(workspace_context.StoredResearchContextService, "build",
        lambda self, ticker, **kwargs: {"ticker": ticker, "events": [], "relations": [],
                                       "source_refs": [], "backends": {}, "excluded": {}})


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


class FakeAssetEvidenceService:
    def build(self, ticker: str, *, as_of, portfolio=None):
        current = FakeCurrentQuoteProvider().get_current_quote(ticker)
        return AssetEvidencePack(
            ticker=ticker,
            as_of=as_of,
            market={
                "current_quote": current.to_dict(),
                "history_count": 80,
                "history_latest": {
                    "ticker": ticker,
                    "close": 49.1,
                    "source": "oplab",
                    "observation_timestamp": NOW.isoformat(),
                },
                "previous_completed_close": {
                    "ticker": ticker,
                    "close": 48.9,
                    "source": "oplab",
                    "observation_timestamp": NOW.isoformat(),
                },
            },
            quant={"volatility_20d": 0.22, "rsi_14": 52.0},
            fundamentals={"metric_count": 3, "metrics": {}, "provider": "brapi"},
            portfolio={"held": False, "stock_quantity": 0},
            source_refs=("oplab", "brapi"),
            quality_status="WARNING",
            limitations=(),
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


class FakeJoaoMemory:
    def context(self, query: str, **kwargs):
        return {
            "query": query,
            "memories": [
                {
                    "source_ref": "joao-memory:m1",
                    "content": "Pesquisa anterior sobre WEGE3.",
                    "memory_type": "research",
                    "source": "joao-resolve",
                    "score": 0.91,
                }
            ],
            "relations": [],
            "authority": "derived_non_authoritative",
            "source": "joao-memory-api",
            "source_refs": ["joao-memory:m1"],
        }


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


class FakeOpportunityResult:
    class Set:
        source_refs = ("oplab",)

    opportunity_set = Set()
    limitations = ("Stock valuation unavailable.",)


class FakeOpportunityService:
    def build(self, ticker, *, as_of, limit):
        assert ticker == "WEGE3"
        return FakeOpportunityResult()

    def as_payload(self, result):
        return {
            "ticker": "WEGE3",
            "as_of": NOW,
            "opportunity_set": {
                "ranked_opportunities": [
                    {
                        "opportunity_id": "SELL_PUT:WEGEV500",
                        "options_analysis_ref": "WEGEV500",
                        "ticker": "WEGE3",
                        "action": "SELL_PUT",
                    }
                ],
                "ranking_policy_version": "1.0+B3_OPTION_MARKETABILITY_V1",
                "source_refs": ["oplab"],
                "quality_status": "WARNING",
            },
            "option_marketability": {
                "WEGEV500": {"eligible": True, "bid": 1.2}
            },
            "opportunity_ranking_status": "DEFERRED_INCOMPLETE_CONTEXT",
            "opportunity_ranking_reason": (
                "Economic ranking deferred in fake service."
            ),
            "limitations": ["Stock valuation unavailable."],
        }


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
        asset_evidence_service=FakeAssetEvidenceService(),
        joao_memory_client=FakeJoaoMemory(),
        joao_service=FakeJoao(),
    )

    result = service.build(
        workspace="Strategy Lab",
        tickers=("VALE3", "WEGE3"),
        deterministic_result={"fast_route": {"target": "strategy_engine"}},
    )

    assert result.deterministic_context["workspace_result"]["fast_route"]["target"] == "strategy_engine"
    decision_history = result.deterministic_context["decision_history"]
    assert [c["subject_id"] for c in decision_history["candidates"]] == ["VALE3", "WEGE3"]
    assert decision_history["ranking_effect"] == "NONE"
    market = result.deterministic_context["market_analysis"]
    assert market["tickers"]["WEGE3"]["current_quote"]["close"] == 49.4
    assert market["tickers"]["VALE3"]["research_events"][0]["headline"].startswith("VALE3")
    assert market["macro"]["SELIC"]["value"] == 12.0

    local = result.derived_intelligence["b3_local_evidence_analyst"]
    assert local["VALE3"]["status"] == "READY"
    assert local["VALE3"]["analysis"]["summary"] == "Dossier local VALE3"

    memory = result.derived_intelligence["joao_memory_context"]
    assert memory["memories"][0]["source_ref"] == "joao-memory:m1"

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
        asset_evidence_service=FakeAssetEvidenceService(),
        joao_memory_client=FakeJoaoMemory(),
        joao_service=FailingJoao(),
        opportunity_service=FakeOpportunityService(),
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

    workspace_result = result.deterministic_context["workspace_result"]
    opportunity_set = workspace_result["opportunity_set"]
    assert opportunity_set["ranked_opportunities"][0]["opportunity_id"] == "SELL_PUT:WEGEV500"
    assert workspace_result["opportunity_ranking_status"] == "DEFERRED_INCOMPLETE_CONTEXT"
    decision = result.deterministic_context["decision_history"]
    assert decision["candidates"][0]["subject_id"] == "WEGEV500"
    assert decision["candidates"][0]["candidate_id"] == "SELL_PUT:WEGEV500"

    joao = result.derived_intelligence["joao_resolve"]
    assert joao["status"] == "UNAVAILABLE"
    assert any("João Resolve perspective unavailable" in item for item in result.limitations)



def test_joao_perspective_rejects_unknown_source_refs():
    class FakeClient:
        def complete_json(self, **kwargs):
            return {
                "summary": "Perspective",
                "market_observations": [],
                "risks": [],
                "contradictions": [],
                "questions_for_b3": [],
                "source_refs": ["https://invented.test/source"],
            }

    service = JoaoResolvePerspectiveService(client=FakeClient())
    try:
        service.analyze(
            {
                "workspace": "Market Intelligence",
                "source_refs": ["https://example.test/known"],
            }
        )
    except RuntimeError as exc:
        assert "outside the supplied evidence" in str(exc)
    else:
        raise AssertionError("unknown João source refs must be rejected")



def test_joao_memory_client_bounds_fields_and_emits_provenance(monkeypatch):
    payload = {
        "query": "WEGE3",
        "memories": [
            {
                "id": "abc",
                "content": "Relevant prior research",
                "memory_type": "research",
                "source": "joao-resolve",
                "importance": 0.8,
                "score": 0.9,
                "created_at": "2026-09-30T10:00:00Z",
                "metadata_json": "{\"private\": \"not forwarded\"}",
            }
        ],
        "relations": [
            {
                "source_entity": "WEGE3",
                "relation": "RELATED_TO",
                "id": "sector-industrials",
                "name": "Industrials",
                "private_field": "not forwarded",
            }
        ],
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return __import__("json").dumps(payload).encode("utf-8")

    monkeypatch.setattr(
        "b3_agent.intelligence.workspace_context.urllib.request.urlopen",
        lambda request, timeout: Response(),
    )
    result = JoaoMemoryContextClient(
        base_url="http://127.0.0.1:8091",
    ).context("WEGE3 research")

    assert result["source_refs"] == ["joao-memory:abc"]
    assert result["memories"][0]["content"] == "Relevant prior research"
    assert "metadata_json" not in result["memories"][0]
    assert "private_field" not in result["relations"][0]


def test_live_workspace_research_uses_post_fetch_cutoff():
    class FreshNewsProvider:
        last_diagnostics = None

        def search(self, ticker: str, *, query=None, limit=20):
            fresh = datetime.now(timezone.utc)
            return (
                NewsEvidence(
                    instrument_id=ticker,
                    ticker=ticker,
                    observation_timestamp=fresh,
                    available_timestamp=fresh,
                    source="fresh-test",
                    ingested_at=fresh,
                    source_record_id=f"{ticker}:fresh",
                    headline="Mercado atualiza expectativas",
                    source_name="fresh-test",
                    url=f"https://example.test/{ticker}/fresh",
                    published_date=fresh.date(),
                    published_at=fresh,
                    event_type="NEWS",
                    summary="Evidência capturada durante a requisição interativa.",
                ),
            )

    service = WorkspaceIntelligenceContextService(
        news_provider=FreshNewsProvider(),
        fallback_news_provider=FreshNewsProvider(),
        macro_repository=FakeMacroRepository(),
        joao_memory_client=FakeJoaoMemory(),
        joao_service=FailingJoao(),
    )
    result = service.build(
        workspace="Market Intelligence",
        tickers=(),
        deterministic_result={},
        include_joao=False,
    )

    market = result.deterministic_context["market_analysis"]
    assert len(market["market_overview_research"]) >= 1
    assert market["market_overview_research"][0]["source_name"] == "fresh-test"


def test_market_intelligence_filters_undated_generic_pages_from_recent_events():
    class MixedNewsProvider:
        last_diagnostics = None

        def search(self, ticker: str, *, query=None, limit=20):
            return (
                NewsEvidence(
                    instrument_id=ticker,
                    ticker=ticker,
                    observation_timestamp=NOW,
                    available_timestamp=NOW,
                    source="searxng",
                    ingested_at=NOW,
                    source_record_id=f"{ticker}:generic",
                    headline="Cotações de ações ao vivo",
                    source_name="generic",
                    url="https://example.test/cotacoes",
                    published_date=None,
                    published_at=None,
                    event_type="NEWS",
                    summary="Página genérica de cotações.",
                ),
                NewsEvidence(
                    instrument_id=ticker,
                    ticker=ticker,
                    observation_timestamp=NOW,
                    available_timestamp=NOW,
                    source="searxng",
                    ingested_at=NOW,
                    source_record_id=f"{ticker}:dated",
                    headline="Ibovespa reage a juros e fluxo estrangeiro",
                    source_name="dated-news",
                    url="https://example.test/noticia",
                    published_date=NOW.date(),
                    published_at=NOW,
                    event_type="NEWS",
                    summary="Notícia datada sobre o mercado.",
                ),
            )

    service = WorkspaceIntelligenceContextService(
        news_provider=MixedNewsProvider(),
        fallback_news_provider=MixedNewsProvider(),
        macro_repository=FakeMacroRepository(),
        joao_memory_client=FakeJoaoMemory(),
        joao_service=FailingJoao(),
    )
    result = service.build(
        workspace="Market Intelligence",
        tickers=(),
        deterministic_result={},
        include_joao=False,
    )
    events = result.deterministic_context["market_analysis"][
        "market_overview_research"
    ]
    assert events
    assert all(item["source_name"] != "generic" for item in events)
    assert events[0]["source_name"] == "dated-news"
