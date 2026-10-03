from datetime import datetime, timezone, timedelta
from b3_agent.dividend_evidence import dividend_payload

NOW = datetime(2026, 10, 3, 22, tzinfo=timezone.utc)

def event(**changes):
    return {"ticker":"ITUB4", "gross_amount":1., "observation_timestamp":NOW-timedelta(days=2), "available_timestamp":NOW, "source":"fixture", "source_record_id":"event:1", "quality_status":"WARNING", "currency":"BRL", "payment_type":"JCP", "announcement_date":"2026-10-01", "record_date":"2026-10-05", "ex_date":"2026-10-06", "payment_date":"2026-10-30", **changes}

def project(*events):
    return dividend_payload("ITUB4", {"status":"READ_OK", "records":list(events)}, NOW)

def test_announced_payment_with_past_record_does_not_fund_new_purchase():
    result=project(event(record_date="2026-10-02",ex_date="2026-10-03"))
    assert result["events"][0]["new_purchase_entitlement"]=="EXCLUDED_FOR_NEW_PURCHASE"
    assert result["announced_conditional_gross_per_share_brl"] is None

def test_duplicate_records_count_once_and_preserve_source():
    result=project(event(),event(source_record_id="event:copy"))
    assert len(result["events"])==1
    assert result["announced_conditional_gross_per_share_brl"]==1
    assert result["exclusions"][0]["reason"]=="DUPLICATE_DISTRIBUTION"
    assert result["events"][0]["source_record_id"]=="event:1"

def test_future_availability_invalid_amount_foreign_or_rejected_are_excluded():
    for changes in ({"available_timestamp":NOW+timedelta(seconds=1)}, {"gross_amount":float("nan")}, {"currency":"USD"}, {"ticker":"BBDC4"}, {"quality_status":"REJECTED"}, {"payment_date":"bad-date"}, {"payment_date":"2026-09-30"}):
        assert not project(event(**changes))["events"]

def test_empty_or_failed_collection_is_not_zero_income():
    for status in ("READ_OK","PROVIDER_UNAVAILABLE","UNSUPPORTED_PROVIDER"):
        result=dividend_payload("ITUB4",{"status":status,"records":[]},NOW)
        assert result["collection_status"]==status
        assert result["observed_paid_365d_gross_per_share_brl"] is None
        assert result["net_amount"] is None

def test_paid_observations_not_future_income_same_day_entitlement_unknown():
    past=event(payment_date="2026-10-02",record_date="2026-10-01",ex_date="2026-10-02")
    same_day=event(record_date="2026-10-03",ex_date="2026-10-04",source_record_id="event:2")
    result=project(past,same_day)
    assert result["observed_paid_365d_gross_per_share_brl"]==1
    assert result["events"][1]["new_purchase_entitlement"]=="UNKNOWN"
    assert result["announced_conditional_gross_per_share_brl"] is None

def test_brazil_date_controls_entitlement_across_utc_midnight():
    cutoff=datetime(2026,10,4,1,tzinfo=timezone.utc)
    result=dividend_payload("ITUB4",{"status":"READ_OK","records":[event(record_date="2026-10-04",ex_date="2026-10-05")]},cutoff)
    assert result["events"][0]["new_purchase_entitlement"]=="CONDITIONAL_FUTURE_RECORD_DATE"
