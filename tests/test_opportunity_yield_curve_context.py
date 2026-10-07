from datetime import datetime, timezone

from b3_agent.intelligence import workspace_context as module
from b3_agent.intelligence.workspace_context import WorkspaceIntelligenceContextService
from b3_agent.providers.b3_yield_curve import YieldCurveProviderError
from b3_agent.schemas.yield_curve import YieldCurvePoint


NOW = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)


def point(curve):
    return YieldCurvePoint(
        instrument_id=f"ETTJ-{curve}-365",
        ticker=f"ETTJ-{curve}",
        observation_timestamp=NOW,
        available_timestamp=NOW,
        source="b3_taxaswap_pyettj",
        ingested_at=NOW,
        source_record_id=f"b3:taxaswap:2026-10-07:{curve}:365",
        curve_code=curve,
        curve_description="DI x pre" if curve == "PRE" else "DI x IPCA",
        days_calendar=365,
        days_business=252,
        rate_decimal=0.12 if curve == "PRE" else 0.06,
        vertex="1Y",
    )


class FakeMacroRepository:
    def latest(self, indicator):
        return None


class FakeStoredResearch:
    def build(self, ticker, *, as_of, limit):
        return {"events": [], "source_refs": []}


class FakeHistory:
    def __init__(self, data_dir):
        pass

    def build(self, *, ticker=None, as_of=None, since=None):
        return {"source_refs": []}


class FakeYieldCurve:
    def get_latest(self, curve):
        return [point(curve)]


def build_service(monkeypatch, curve_provider):
    monkeypatch.setattr(module, "PersonalHistoryService", FakeHistory)
    monkeypatch.setattr(module, "build_decision_history", lambda *args, **kwargs: {})
    return WorkspaceIntelligenceContextService(
        macro_repository=FakeMacroRepository(),
        stored_research_service=FakeStoredResearch(),
        yield_curve_provider=curve_provider,
    )


def test_opportunity_context_includes_b3_pre_and_dic_vertices(monkeypatch):
    service = build_service(monkeypatch, FakeYieldCurve())

    context = service.build(
        workspace="Opportunities",
        tickers=(),
        include_joao=False,
        include_joao_perspective=False,
        research_mode="stored_only",
        include_yield_curve=True,
    )

    curves = context.deterministic_context["market_analysis"]["macro"]["yield_curves"]
    assert curves["PRE"]["status"] == "AVAILABLE"
    assert curves["PRE"]["points"][0]["days_business"] == 252
    assert curves["DIC"]["status"] == "AVAILABLE"
    assert "b3:taxaswap:2026-10-07:PRE:365" in context.source_refs
    assert "b3:taxaswap:2026-10-07:DIC:365" in context.source_refs


def test_missing_curve_is_exposed_as_a_localized_status(monkeypatch):
    class PartialYieldCurve:
        def get_latest(self, curve):
            if curve == "DIC":
                raise YieldCurveProviderError("NO_DATA", "Sem publicação para a data.")
            return [point(curve)]

    service = build_service(monkeypatch, PartialYieldCurve())
    context = service.build(
        workspace="Opportunities",
        tickers=(),
        include_joao=False,
        include_joao_perspective=False,
        research_mode="stored_only",
        include_yield_curve=True,
    )

    curves = context.deterministic_context["market_analysis"]["macro"]["yield_curves"]
    assert curves["PRE"]["status"] == "AVAILABLE"
    assert curves["DIC"]["status"] == "NO_DATA"
    assert curves["DIC"]["points"] == []
    assert any("Future yield curve DIC unavailable" in item for item in context.limitations)
