"""Observed issuer distributions, separate from forecasts and personal receipts."""
from datetime import date, timedelta, timezone
from b3_agent.stock_purchase import _number, _timestamp


def _date(value):
    if isinstance(value, date):
        return date.fromisoformat(value.isoformat()[:10])
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def dividend_payload(ticker, evidence, cutoff):
    today = cutoff.astimezone(timezone(timedelta(hours=-3))).date()
    events, exclusions, seen = [], [], set()
    outside_window_count = 0
    for raw in evidence.get("records", []):
        amount = _number(raw.get("gross_amount"))
        observed = _timestamp(raw.get("observation_timestamp"))
        available = _timestamp(raw.get("available_timestamp"))
        announced = _date(raw.get("announcement_date"))
        payment = _date(raw.get("payment_date"))
        record = _date(raw.get("record_date"))
        ex_date = _date(raw.get("ex_date"))
        if (raw.get("ticker") != ticker or amount is None or amount < 0
                or not observed or not available or observed > cutoff or available > cutoff
                or not raw.get("source") or not raw.get("source_record_id")
                or raw.get("quality_status") == "REJECTED" or raw.get("currency") != "BRL"
                or any(raw.get(name) is not None and _date(raw[name]) is None for name in ("announcement_date", "payment_date", "record_date", "ex_date"))
                or (announced and payment and payment < announced)
                or (announced and announced > today)
                or (record and ex_date and record >= ex_date)):
            exclusions.append({"source_record_id": raw.get("source_record_id"), "reason": "UNQUALIFIED_OR_INCONSISTENT_DISTRIBUTION"})
            continue
        if payment and payment <= today-timedelta(days=365):
            outside_window_count += 1
            continue
        key = (ticker, raw.get("payment_type"), announced, payment, record, ex_date, amount, raw.get("currency"))
        if key in seen:
            exclusions.append({"source_record_id": raw.get("source_record_id"), "reason": "DUPLICATE_DISTRIBUTION"})
            continue
        seen.add(key)
        if not payment:
            status = "UNKNOWN_PAYMENT_DATE"
        elif payment <= today:
            status = "PAST_OR_CURRENT_PAYMENT"
        else:
            status = "ANNOUNCED_FUTURE_PAYMENT" if announced else "FUTURE_PAYMENT_UNVERIFIED_ANNOUNCEMENT"
        eligibility = "UNKNOWN"
        if (record and record < today) or (ex_date and ex_date <= today):
            eligibility = "EXCLUDED_FOR_NEW_PURCHASE"
        elif record and record > today and ex_date and ex_date > record:
            eligibility = "CONDITIONAL_FUTURE_RECORD_DATE"
        events.append({"gross_amount_per_share_brl": amount, "payment_type": raw.get("payment_type"),
            "announcement_date": announced, "record_date": record, "ex_date": ex_date, "payment_date": payment,
            "payment_status": status, "new_purchase_entitlement": eligibility,
            "source": raw["source"], "source_record_id": raw["source_record_id"],
            "available_timestamp": available, "quality_status": raw.get("quality_status"),
            "quality_flags": raw.get("quality_flags", [])})
    trailing = [event for event in events if event["payment_date"] and today-timedelta(days=365) < event["payment_date"] <= today]
    possible = [event for event in events if event["payment_status"] == "ANNOUNCED_FUTURE_PAYMENT" and event["new_purchase_entitlement"] == "CONDITIONAL_FUTURE_RECORD_DATE"]
    return {"policy_version": "issuer-dividends-v1", "collection_status": evidence.get("status", "UNKNOWN"),
        "read_origin": evidence.get("read_origin"), "snapshot_available_at": evidence.get("snapshot_available_at"),
        "snapshot_document_id": evidence.get("snapshot_document_id"),
        "events": events, "exclusions": exclusions, "outside_window_count": outside_window_count,
        "provider_error_type": evidence.get("error_type"), "provider_http_status": evidence.get("http_status"),
        "observed_paid_365d_gross_per_share_brl": sum(event["gross_amount_per_share_brl"] for event in trailing) if trailing else None,
        "announced_conditional_gross_per_share_brl": sum(event["gross_amount_per_share_brl"] for event in possible) if possible else None,
        "coverage_status": evidence.get("coverage_status", "UNKNOWN_PROVIDER_COMPLETENESS"), "net_amount": None,
        "limitations": ["Observed distributions are issuer events, not personal received income or a dividend forecast.",
            "Future record-date entitlement is conditional on a timely eligible purchase, settlement and issuer rules; same-day or missing dates remain UNKNOWN.",
            "Absent events do not establish zero dividends. Provider completeness and net taxes remain UNKNOWN."]}
