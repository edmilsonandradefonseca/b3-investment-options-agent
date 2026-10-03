from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from fastapi.testclient import TestClient

from b3_agent import server
from b3_agent.orchestration import OrchestratorResponse
from b3_agent.schemas.fundamental import StockFundamental


client = TestClient(server.app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "b3-orchestrator-server"


def test_version_endpoint() -> None:
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "service": "b3-orchestrator-server",
        "version": server.app.version,
    }


def test_orchestrate_delegates_to_logical_contract(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_configure() -> None:
        calls["configured"] = True

    def fake_orchestrator(*, task: str, ticker: str | None, context: dict) -> OrchestratorResponse:
        calls["request"] = {"task": task, "ticker": ticker, "context": context}
        return OrchestratorResponse(
            status="COMPLETED",
            result={"decision_proposal": {"action": "HOLD"}},
            sources=("obsidian/test.md",),
        )

    monkeypatch.setattr(server, "_configure_runtime", fake_configure)
    monkeypatch.setattr(server, "b3_orchestrator", fake_orchestrator)

    response = client.post(
        "/orchestrate",
        json={"task": "Analyze ITUB4", "ticker": "itub4", "context": {"foo": "bar"}},
    )

    assert response.status_code == 200
    assert calls["configured"] is True
    assert calls["request"] == {
        "task": "Analyze ITUB4",
        "ticker": "ITUB4",
        "context": {"foo": "bar"},
    }
    assert response.json()["status"] == "COMPLETED"
    assert response.json()["result"]["decision_proposal"]["action"] == "HOLD"
    assert response.json()["sources"] == ["obsidian/test.md"]


def test_orchestrate_rejects_unknown_fields() -> None:
    response = client.post("/orchestrate", json={"task": "Analyze", "unknown": True})

    assert response.status_code == 422


def test_orchestrate_reports_runtime_configuration_failure(monkeypatch) -> None:
    def fail_configure() -> None:
        raise RuntimeError("B3_AGENT_OBSIDIAN_VAULT is not configured")

    monkeypatch.setattr(server, "_configure_runtime", fail_configure)

    response = client.post("/orchestrate", json={"task": "Analyze ITUB4"})

    assert response.status_code == 503
    assert "OBSIDIAN_VAULT" in response.json()["detail"]



def test_replace_validated_upload_preserves_excel_extension(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(server, "_import_dir", lambda: tmp_path)
    seen: dict[str, str] = {}

    def validator(path: Path) -> None:
        seen["suffix"] = path.suffix
        seen["content"] = path.read_bytes().decode("utf-8")

    upload = UploadFile(filename="portfolio.xlsx", file=BytesIO(b"excel-bytes"))
    result = server._replace_validated_upload(upload, "portfolio.xlsx", validator)

    assert seen == {"suffix": ".xlsx", "content": "excel-bytes"}
    assert result["status"] == "replaced"
    assert (tmp_path / "portfolio.xlsx").read_bytes() == b"excel-bytes"


def test_runtime_status_endpoint(monkeypatch, tmp_path: Path) -> None:
    class FakeRuntimeManager:
        def status(self, *, health_override: str | None = None):
            assert health_override == "ok"
            return {
                "runtime": "running",
                "runtime_root": str(tmp_path),
                "health": "ok",
                "resources": {
                    "filesystem": "ok",
                    "sqlite": "ok",
                    "parquet": "ok",
                },
                "services": {
                    "qdrant": {"state": "ok", "ownership": "shared_external"},
                    "neo4j": {"state": "ok", "ownership": "shared_external"},
                },
                "process": {"running": True},
            }

    monkeypatch.setattr(server, "RuntimeManager", FakeRuntimeManager)
    response = client.get("/runtime/status")

    assert response.status_code == 200
    body = response.json()
    assert body["runtime"] == "running"
    assert body["health"] == "ok"
    assert body["resources"]["sqlite"] == "ok"
    assert body["services"]["qdrant"]["ownership"] == "shared_external"


def test_orchestrate_fast_route_skips_llm_runtime(monkeypatch) -> None:
    def fail_configure() -> None:
        raise AssertionError("LLM runtime must not be configured for deterministic fast route")

    def fail_orchestrator(*args, **kwargs):
        raise AssertionError("senior LLM workflow must not run for deterministic fast route")

    monkeypatch.setattr(
        server,
        "_dispatch_fast_route",
        lambda request: OrchestratorResponse(
            status="COMPLETED",
            result={
                "fast_route": {
                    "target": "portfolio_engine",
                    "use_case": "UC-01",
                },
                "portfolio_context": {"quality_status": "VALIDATED"},
            },
            sources=("BTG:Renda Variavel:Acoes",),
            audit=({"event": "fast_router_dispatch"},),
        ),
    )
    monkeypatch.setattr(server, "_configure_runtime", fail_configure)
    monkeypatch.setattr(server, "b3_orchestrator", fail_orchestrator)

    response = client.post(
        "/orchestrate",
        json={
            "task": "Resuma o estado atual da carteira",
            "context": {
                "dashboard_page": "Portfolio",
                "use_cases": ["UC-01"],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["result"]["fast_route"]["target"] == "portfolio_engine"
    assert body["audit"][0]["event"] == "fast_router_dispatch"



def test_strategy_lab_preserves_fast_facts_and_adds_senior_workspace_intelligence(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeContext:
        workspace = "Strategy Lab"
        as_of = __import__("datetime").datetime(2026, 10, 1, 17, 0, tzinfo=__import__("datetime").timezone.utc)
        tickers = ("VALE3", "WEGE3")
        derived_intelligence = {
            "b3_local_evidence_analyst": {},
            "joao_resolve": {
                "status": "READY",
                "authority": "derived_non_authoritative",
                "summary": "João perspective",
            },
        }
        source_refs = ("oplab", "bcb_sgs")
        limitations = ()

        def as_context(self):
            return {
                "workspace_intelligence": True,
                "deterministic_context": {
                    "workspace": "Strategy Lab",
                    "workspace_result": {
                        "fast_route": {"target": "strategy_engine"},
                        "asset_evidence": {"VALE3": {}, "WEGE3": {}},
                    },
                },
                "derived_intelligence": self.derived_intelligence,
                "workspace_intelligence_meta": {
                    "workspace": self.workspace,
                    "tickers": list(self.tickers),
                },
            }

    class FakeService:
        def build(self, **kwargs):
            calls["build"] = kwargs
            return FakeContext()

    monkeypatch.setattr(server, "WorkspaceIntelligenceContextService", FakeService)
    monkeypatch.setattr(
        server,
        "_dispatch_fast_route",
        lambda request: OrchestratorResponse(
            status="COMPLETED",
            result={
                "fast_route": {"target": "strategy_engine", "use_case": "UC-04"},
                "asset_evidence": {"VALE3": {"fact": 1}, "WEGE3": {"fact": 2}},
            },
            sources=("oplab",),
            audit=({"event": "fast_router_dispatch"},),
        ),
    )
    monkeypatch.setattr(server, "_configure_runtime", lambda: calls.setdefault("configured", True))

    def fake_orchestrator(*, task, ticker, context):
        calls["senior_context"] = context
        return OrchestratorResponse(
            status="PASS",
            result={
                "market_agent_analysis": {"summary": "market"},
                "synthesis": {"summary": "senior synthesis"},
                "proposal": {"action": "WAIT"},
            },
            sources=("qdrant:evidence",),
            audit=({"event": "senior_reasoning"},),
        )

    monkeypatch.setattr(server, "b3_orchestrator", fake_orchestrator)

    response = client.post(
        "/orchestrate",
        json={
            "task": "Compare as alternativas com inteligência de mercado",
            "context": {
                "workspace": "Strategy Lab",
                "comparison_assets": ["VALE3", "WEGE3"],
                "strategy_a": "Comprar ação",
                "strategy_b": "Comprar ação",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["fast_route"]["target"] == "strategy_engine"
    assert body["result"]["asset_evidence"]["VALE3"]["fact"] == 1
    assert body["result"]["synthesis"]["summary"] == "senior synthesis"
    assert body["result"]["workspace_intelligence"]["derived_intelligence"]["joao_resolve"]["status"] == "READY"
    senior_context = calls["senior_context"]
    assert senior_context["deterministic_context"]["workspace_result"]["fast_route"]["target"] == "strategy_engine"
    assert senior_context["derived_intelligence"]["joao_resolve"]["authority"] == "derived_non_authoritative"
    assert any(item["event"] == "workspace_intelligence_composed" for item in body["audit"])


def test_opportunities_workspace_runs_intelligence_even_without_fast_route(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeContext:
        workspace = "Opportunities"
        as_of = __import__("datetime").datetime(2026, 10, 1, 17, 0, tzinfo=__import__("datetime").timezone.utc)
        tickers = ("WEGE3",)
        derived_intelligence = {"joao_resolve": {"status": "READY"}}
        source_refs = ("oplab",)
        limitations = ("No canonical stock valuation supplied.",)

        def as_context(self):
            return {
                "workspace_intelligence": True,
                "deterministic_context": {
                    "workspace": "Opportunities",
                    "workspace_result": {
                        "opportunity_set": {
                            "ranked_opportunities": [
                                {
                                    "opportunity_id": "SELL_PUT:WEGEV500",
                                    "ticker": "WEGE3",
                                    "action": "SELL_PUT",
                                }
                            ],
                            "ranking_policy_version": "1.0+B3_OPTION_MARKETABILITY_V1",
                        },
                        "option_marketability": {
                            "WEGEV500": {"eligible": True, "bid": 1.2}
                        },
                    },
                    "market_analysis": {
                        "tickers": {
                            "WEGE3": {
                                "asset_evidence": {
                                    "ticker": "WEGE3",
                                    "market": {
                                        "current_quote": {
                                            "source": "oplab",
                                            "close": 49.4,
                                        }
                                    },
                                }
                            }
                        }
                    },
                },
                "derived_intelligence": self.derived_intelligence,
            }

    class FakeService:
        def build(self, **kwargs):
            calls["build"] = kwargs
            return FakeContext()

    monkeypatch.setattr(server, "WorkspaceIntelligenceContextService", FakeService)
    monkeypatch.setattr(server, "_dispatch_fast_route", lambda request: None)
    monkeypatch.setattr(server, "_configure_runtime", lambda: None)
    monkeypatch.setattr(
        server,
        "b3_orchestrator",
        lambda **kwargs: OrchestratorResponse(
            status="PASS",
            result={"synthesis": {"summary": "Opportunity intelligence"}},
            sources=("qdrant:evidence",),
        ),
    )

    response = client.post(
        "/orchestrate",
        json={
            "task": "UC-03 analise WEGE3",
            "ticker": "WEGE3",
            "context": {"workspace": "Opportunities", "selected_ticker": "WEGE3"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["synthesis"]["summary"] == "Opportunity intelligence"
    assert body["result"]["workspace_intelligence"]["workspace"] == "Opportunities"
    assert body["result"]["opportunity_set"]["ranked_opportunities"][0]["opportunity_id"] == "SELL_PUT:WEGEV500"
    assert body["result"]["option_marketability"]["WEGEV500"]["bid"] == 1.2
    assert body["result"]["workspace_intelligence"]["limitations"] == [
        "No canonical stock valuation supplied."
    ]
    assert body["result"]["asset_evidence"]["WEGE3"]["market"]["current_quote"]["source"] == "oplab"


def test_live_analysis_returns_pit_history_and_backend_indicators(monkeypatch) -> None:
    from datetime import datetime, timedelta, timezone
    from b3_agent.options.analysis import OptionsAnalysis
    from b3_agent.schemas.market import StockMarketData

    as_of = datetime.now(timezone.utc) - timedelta(seconds=2)
    history = tuple(
        StockMarketData(
            instrument_id="PETR4",
            ticker="PETR4",
            observation_timestamp=as_of - timedelta(days=40 - index),
            available_timestamp=as_of - timedelta(days=40 - index),
            source="test-history",
            ingested_at=as_of - timedelta(days=40 - index),
            source_record_id=f"petr4:{index}",
            open=20 + index,
            high=21 + index,
            low=19 + index,
            close=20 + index,
            volume=1000,
        )
        for index in range(40)
    )
    acquired_at = datetime.now(timezone.utc)
    fetched = StockMarketData(
        instrument_id="PETR4",
        ticker="PETR4",
        observation_timestamp=acquired_at,
        available_timestamp=acquired_at,
        source="oplab",
        ingested_at=acquired_at,
        source_record_id="petr4:fetched-after-initial-as-of",
        open=60,
        high=61,
        low=59,
        close=60,
        volume=2000,
    )
    future = StockMarketData(
        instrument_id="PETR4",
        ticker="PETR4",
        observation_timestamp=acquired_at + timedelta(days=1),
        available_timestamp=acquired_at + timedelta(days=1),
        source="test-history",
        ingested_at=acquired_at + timedelta(days=1),
        source_record_id="petr4:future",
        open=999,
        high=999,
        low=999,
        close=999,
        volume=1000,
    )
    snapshot = type("Snapshot", (), {
        "ticker": "PETR4",
        "as_of": as_of,
        "market_records": history + (fetched, future),
        "current_stock_quote": None,
        "option_contracts": (),
        "option_quotes": (),
        "options_analysis": OptionsAnalysis(),
        "source_refs": ("test-history", "oplab"),
    })()

    class FakeLiveProviderService:
        def load(self, ticker, *, include_current_quote, include_options):
            assert ticker == "PETR4"
            assert include_current_quote is False
            assert include_options is False
            return snapshot

    monkeypatch.setattr(server, "LiveProviderService", FakeLiveProviderService)
    response = client.get("/analysis/live/PETR4")

    assert response.status_code == 200
    body = response.json()
    assert body["market"]["history_count"] == 41
    assert len(body["market"]["price_history"]) == 41
    assert body["market"]["price_history"][-1]["close"] == 60
    assert body["market"]["price_history"][-1]["source_record_id"] == fetched.source_record_id
    assert body["market"]["quant"]["data_points"] == 41
    assert body["market"]["latest"]["source_record_id"] == fetched.source_record_id
    assert datetime.fromisoformat(body["as_of"]) >= acquired_at

def test_current_fundamentals_exposes_source_and_excludes_future_records(monkeypatch) -> None:
    now = datetime.now(timezone.utc)

    def record(metric: str, value: float, observed: datetime) -> StockFundamental:
        return StockFundamental(
            instrument_id="VALE3",
            ticker="VALE3",
            observation_timestamp=observed,
            available_timestamp=observed,
            source="brapi",
            ingested_at=observed,
            source_record_id=f"VALE3:{metric}",
            quality_status="WARNING",
            quality_flags=("availability_is_ingestion_time",),
            metric=metric,
            value=value,
            report_date=observed.date(),
            period_type="TTM",
            unit="ratio",
        )

    class FakeFundamentals:
        def get_financial_data(self, ticker: str):
            assert ticker == "VALE3"
            return [
                record("priceEarnings", 4.2, now),
                record("futureMetric", 1.0, now + timedelta(days=1)),
            ]

    monkeypatch.setattr(server, "BrapiFundamentalsAdapter", FakeFundamentals)
    response = client.get("/fundamentals/vale3")

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "VALE3"
    assert body["status"] == "AVAILABLE"
    assert body["excluded_future_count"] == 1
    assert [item["metric"] for item in body["metrics"]] == ["priceEarnings"]
    assert body["metrics"][0]["quality_flags"] == ["availability_is_ingestion_time"]
    assert body["source_refs"] == ["brapi:VALE3:priceEarnings"]
    assert any("historical availability" in item for item in body["limitations"])


def test_current_fundamentals_rejects_invalid_b3_symbol() -> None:
    response = client.get("/fundamentals/WWEGE3")

    assert response.status_code == 400
