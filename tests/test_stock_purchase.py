from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from b3_agent.stock_purchase import stock_purchase_payload

NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)

def build(**changes):
    metric = {"value": 10., "unit": "ratio", "report_date": "2026-09-30", "period_type": "TTM", "available_timestamp": NOW, "source": "fixture", "quality_status": "WARNING"}
    metric.update(changes)
    pack = SimpleNamespace(ticker="ITUB4", market={"current_quote": {"close": 30., "observation_timestamp": NOW, "available_timestamp": NOW}, "history_start": "2026-07-01", "history_end": "2026-10-02"}, fundamentals={"metrics": {"priceEarnings": metric}}, quant={}, portfolio={}, source_refs=("fixture",))
    alt = SimpleNamespace(alternative_id="A", capital_required=1000., evidence_refs=("evidence:A",))
    return pack, alt

def test_equal_period_metrics_compare_without_fabricating_forecast():
    pack, alt = build()
    result = stock_purchase_payload([alt, alt], [pack, pack], NOW)
    assert result["fundamental_comparisons"][0]["right_minus_left"] == 0
    assert result["observed_risk_same_window"]
    assert result["rows"][0]["future_dividend_per_share"] is None
    assert result["rows"][0]["positive_return_probability"] is None
    assert result["ranking"].startswith("UNKNOWN")

def test_future_available_fundamental_cannot_enter_senior_projection():
    pack, alt = build(available_timestamp=NOW + timedelta(seconds=1))
    result = stock_purchase_payload([alt, alt], [pack, pack], NOW)
    assert result["rows"][0]["fundamental_metrics"] == {}
    assert result["rows"][0]["excluded_metrics"]

def test_mismatched_period_missing_unit_and_future_report_do_not_compare():
    pack, alt = build()
    for changes in ({"period_type": "Q"}, {"unit": None}, {"report_date": "2026-10-04"}):
        other, _ = build(**changes)
        result = stock_purchase_payload([alt, alt], [pack, other], NOW)
        assert result["fundamental_comparisons"][0]["right_minus_left"] is None

def test_stale_future_or_unavailable_quote_is_not_current_price():
    pack, alt = build()
    for change in ({"observation_timestamp": NOW-timedelta(days=8)}, {"available_timestamp": NOW+timedelta(seconds=1)}, {"close": float("nan")}):
        pack.market["current_quote"] = {"close": 30., "observation_timestamp": NOW, "available_timestamp": NOW, **change}
        assert stock_purchase_payload([alt,alt], [pack,pack], NOW)["rows"][0]["current_price_brl"] is None


def test_fundamental_report_date_uses_sao_paulo_calendar_cutoff():
    cutoff = datetime(2026, 10, 5, 0, 23, tzinfo=timezone.utc)  # Oct 4, 21:23 in São Paulo
    pack, alt = build(report_date="2026-10-05", available_timestamp=cutoff)
    result = stock_purchase_payload([alt, alt], [pack, pack], cutoff)

    assert result["rows"][0]["fundamental_metrics"] == {}
    excluded = result["rows"][0]["excluded_metrics"][0]
    assert excluded["report_date"] == "2026-10-05"
    assert excluded["reason"] == "UNQUALIFIED_OR_FUTURE_FUNDAMENTAL"
