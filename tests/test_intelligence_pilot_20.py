from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


script_path = Path(__file__).resolve().parents[1] / "scripts" / "intelligence_pilot_20.py"
spec = spec_from_file_location("intelligence_pilot_20", script_path)
pilot = module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(pilot)


class FakeSenior:
    def __init__(self):
        self.calls = 0

    def complete_json(self, **kwargs):
        self.calls += 1
        return {"summary": "Supported", "risks": [], "catalysts": [], "limitations": [],
                "evidence_refs": ["https://example.test/event"]}


def test_20_stock_route_coverage():
    assert len(pilot.TICKERS) == 20
    for ticker in pilot.TICKERS:
        routes = pilot.routing_contract(ticker)
        assert routes == {"market": "market_provider", "research": "deepseek-r1:8b", "senior": "openclaw"}


def test_no_material_event_does_not_call_either_model(tmp_path, monkeypatch):
    class FakeNightly:
        def __init__(self, **kwargs):
            pass

        def run(self, **kwargs):
            return {"results": [{"status": "skipped_no_material_events", "as_of": "2026-09-29T18:00:00+00:00"}]}

    monkeypatch.setattr(pilot, "NightlyIntelligenceJob", FakeNightly)
    monkeypatch.setattr(pilot, "market_evidence", lambda ticker: {"close": 1, "as_of": "2026-09-29"})
    senior = FakeSenior()
    row = pilot.analyze("ABEV3", tmp_path, senior)
    assert row["deepseek_status"] == "skipped_no_material_events"
    assert row["escalation_status"] == "not_required"
    assert senior.calls == 0


def test_material_dossier_escalates_with_provenance(tmp_path, monkeypatch):
    class FakeNightly:
        def __init__(self, **kwargs):
            pass

        def run(self, **kwargs):
            return {"results": [{"status": "completed", "as_of": "2026-09-29T18:00:00+00:00",
                                 "source_refs": ["https://example.test/event"],
                                 "evidence_events": [{"headline": "Material", "source_ref": "https://example.test/event"}],
                                 "model": "deepseek-r1:8b", "analysis": "Dossier"}]}

    monkeypatch.setattr(pilot, "NightlyIntelligenceJob", FakeNightly)
    monkeypatch.setattr(pilot, "market_evidence", lambda ticker: {"close": 1, "as_of": "2026-09-29"})
    senior = FakeSenior()
    row = pilot.analyze("ABEV3", tmp_path, senior)
    assert row["deepseek_status"] == row["openclaw_status"] == "completed"
    assert row["routes"]["research"] == "deepseek-r1:8b"
    assert senior.calls == 1
    assert pilot.analyze("ABEV3", tmp_path, senior)["openclaw_status"] == "completed"
    assert senior.calls == 1


def test_live_pilot_accepts_explicit_coverage_insufficient_as_observable_state():
    rows = []
    for ticker in pilot.TICKERS[:10]:
        rows.append(
            {
                "ticker": ticker,
                "market": "validated",
                "deepseek": "completed",
                "openclaw": "completed",
            }
        )
    for ticker in pilot.TICKERS[10:15]:
        rows.append(
            {
                "ticker": ticker,
                "market": "validated",
                "deepseek": "skipped_no_material_events",
                "openclaw": "not_required",
            }
        )
    for ticker in pilot.TICKERS[15:]:
        rows.append(
            {
                "ticker": ticker,
                "market": "validated",
                "deepseek": "coverage_insufficient",
                "openclaw": "not_required",
            }
        )

    assert pilot.pilot_runtime_ok(
        rows,
        {"status": "SUCCESS", "resolved_tickers": 20},
    )


def test_live_pilot_still_fails_real_runtime_or_model_errors():
    rows = [
        {
            "ticker": ticker,
            "market": "validated",
            "deepseek": "skipped_no_material_events",
            "openclaw": "not_required",
        }
        for ticker in pilot.TICKERS
    ]
    rows[-1]["deepseek"] = "failed"

    assert not pilot.pilot_runtime_ok(
        rows,
        {"status": "SUCCESS", "resolved_tickers": 20},
    )
