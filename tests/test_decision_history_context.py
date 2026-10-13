from copy import deepcopy
import sqlite3

from b3_agent.intelligence.decision_history import build_decision_history
from b3_agent.intelligence.personal_history import PersonalHistoryService


def source(tmp_path):
    with sqlite3.connect(tmp_path / "options.sqlite3") as conn:
        conn.execute("CREATE TABLE option_transactions (transaction_id TEXT, option_ticker TEXT, broker TEXT, quantity REAL, average_cost REAL, total_cost REAL, as_of TEXT, source_ref TEXT, source_type TEXT, source_id TEXT)")
        conn.executemany("INSERT INTO option_transactions VALUES (?,?,?,?,?,?,?,?,?,?)", [
            ("sell", "PETRA100", "BTG", -100, 2, -200, "2026-01-02", "BTG:NotaCorretagem:1", "BROKERAGE_NOTE", "1"),
            ("buy", "PETRA100", "BTG", 100, 1, 100, "2026-01-10", "BTG:NotaCorretagem:2", "BROKERAGE_NOTE", "2"),
            ("sibling", "PETRA200", "BTG", -100, 3, -300, "2026-01-02", "BTG:NotaCorretagem:3", "BROKERAGE_NOTE", "3"),
        ])
    return PersonalHistoryService(tmp_path)


def comparison(*subjects):
    return {"strategy_comparison": {"alternatives": [
        {"alternative_id": str(i), "subject_id": symbol, "action_type": "SELL_PUT", "historical_similarity": .99}
        for i, symbol in enumerate(subjects)
    ]}}


def test_exact_contract_does_not_admit_sibling_or_infer_learning(tmp_path):
    service = source(tmp_path)
    original = comparison("PETRA100", "PETRA200")
    unchanged = deepcopy(original)
    result = build_decision_history(service, result=original)
    assert original == unchanged
    histories = result["subjects"]
    assert histories["PETRA100"]["execution_count"] == 2
    assert histories["PETRA200"]["execution_count"] == 1
    assert histories["PETRA100"]["observed_sequence_count"] == 1
    assert histories["PETRA100"]["historical_admission"]["eligible_outcome_count"] == 0
    assert histories["PETRA100"]["validated_similarity"] is None
    assert histories["PETRA100"]["net_flat_sequences"][0]["realized_pnl"] is None
    assert result["ranking_effect"] == "NONE"
    assert all(row["identity_match"] == "EXACT_SYMBOL" for h in histories.values() for row in h["executions"])
    # Compatibility retains explicitly unverified asset-root observations.
    assert service.build(ticker="PETR4")["execution_count"] == 3
    assert service.build(ticker="PETR4", exact_symbol=True)["execution_count"] == 0
    assert service.build(ticker="PETRA100")["fingerprint"] != histories["PETRA100"]["fingerprint"]
    assert build_decision_history(service, result=comparison(" "))["subjects"] == {}


def test_opportunities_use_contract_ref_and_preserve_order_and_limits(tmp_path):
    service = source(tmp_path)
    payload = {"opportunity_set": {"ranked_opportunities": [
        {"opportunity_id": str(i), "ticker": "PETR4", "options_analysis_ref": "PETRA100", "action": "SELL_CALL"}
        for i in range(22)
    ]}}
    result = build_decision_history(service, result=payload)
    assert [c["candidate_id"] for c in result["candidates"]] == [str(i) for i in range(20)]
    assert set(result["subjects"]) == {"PETRA100"}
    assert result["candidate_details_omitted"] == 2
    assert result["subjects"]["PETRA100"]["observed_sequences"][0]["observed_direction"] == "SHORT"
    # Current CALL label cannot turn historical symbol into CALL evidence.
    assert "option_type" not in result["subjects"]["PETRA100"]["observed_sequences"][0]


def test_two_actions_on_same_subject_reuse_projection(tmp_path, monkeypatch):
    service = source(tmp_path)
    calls = []
    build = service.build
    def counted(**kwargs):
        calls.append(kwargs)
        return build(**kwargs)
    monkeypatch.setattr(service, "build", counted)
    payload = comparison("PETRA100", "PETRA100")
    payload["strategy_comparison"]["alternatives"][1]["action_type"] = "HOLD"
    result = build_decision_history(service, result=payload)
    assert len(calls) == 1
    assert len(result["candidates"]) == 2


def test_cutoff_requires_import_availability_and_invalidates_on_new_source(tmp_path):
    service = source(tmp_path)
    cutoff = "2026-02-01T00:00:00+00:00"
    result = build_decision_history(service, result=comparison("PETRA100"), as_of=cutoff)
    assert result["subjects"]["PETRA100"]["execution_count"] == 0
    with sqlite3.connect(tmp_path / "source_manifest.sqlite3") as conn:
        conn.execute("CREATE TABLE source_manifest (source_id TEXT, source_type TEXT, imported_at TEXT)")
        conn.executemany("INSERT INTO source_manifest VALUES (?,?,?)", [
            ("1", "BROKERAGE_NOTE", "2026-01-03T00:00:00+00:00"),
            ("2", "BROKERAGE_NOTE", "2026-03-01T00:00:00+00:00"),
        ])
    admitted = build_decision_history(service, result=comparison("PETRA100"), as_of=cutoff)["subjects"]["PETRA100"]
    assert admitted["execution_count"] == 1
    assert admitted["mode"] == "STRICT_KNOWN_AT_TIME"
    assert admitted["fingerprint"] != result["subjects"]["PETRA100"]["fingerprint"]
    assert admitted["historical_admission"]["eligible_outcome_count"] == 0


def test_since_keeps_opening_leg_but_filters_execution_presentation(tmp_path):
    service = source(tmp_path)
    history = build_decision_history(service, result=comparison("PETRA100"), since="2026-01-05")["subjects"]["PETRA100"]
    assert history["execution_count"] == 1
    assert history["observed_sequences"][0]["source_transaction_ids"] == ("sell", "buy")
    assert history["observed_sequences"][0]["economic_outcome_status"] == "UNKNOWN"


def test_empty_source_copilot_is_not_zero_loss_evidence(tmp_path):
    result = build_decision_history(PersonalHistoryService(tmp_path), result={}, tickers=("VALE3",))
    assert result["candidates"][0]["subject_id"] == "VALE3"
    history = result["subjects"]["VALE3"]
    assert history["coverage"] == "UNKNOWN"
    assert history["assignment_frequency"] is None
    assert history["sources"]["option_transactions"]["status"] == "MISSING"
    assert not list(tmp_path.iterdir())
    missing_contract = build_decision_history(PersonalHistoryService(tmp_path), result={
        "opportunity_set": {"ranked_opportunities": [{"opportunity_id": "missing", "ticker": "VALE3", "action": "SELL_PUT"}]}
    }, tickers=("VALE3",))
    assert missing_contract["candidates"][0]["candidate_id"] == "ASSET:VALE3"
    assert missing_contract["candidates"][0]["action"] == "ANALYZE"


def test_read_api_reuses_projection_without_providers_or_writes(tmp_path, monkeypatch):
    import runpy
    from pathlib import Path
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from b3_agent import server

    source(tmp_path)
    before = (tmp_path / "options.sqlite3").read_bytes()
    monkeypatch.setattr(server, "settings", SimpleNamespace(data_dir=tmp_path))
    monkeypatch.setattr(server, "_configure_runtime", lambda: (_ for _ in ()).throw(AssertionError("model invoked")))
    client = TestClient(server.app)
    response = client.get("/history/decision-context", params={"ticker": "petra100"})
    assert response.status_code == 200
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    validator = runpy.run_path(str(scripts / "validate_decision_history_real.py"))["validate"]
    assert validator(response.json(), "PETRA100")["execution_count"] == 2
    strict = client.get("/history/decision-context", params={"ticker": "PETRA100", "as_of": "2026-02-01T00:00:00Z"})
    assert validator(strict.json(), "PETRA100")["execution_count"] == 0
    assert client.get("/history/decision-context", params={"ticker": " "}).status_code == 400
    assert client.get("/history/decision-context", params={"ticker": "PETRA100", "as_of": "2026-02-01T00:00:00"}).status_code == 400
    assert (tmp_path / "options.sqlite3").read_bytes() == before
