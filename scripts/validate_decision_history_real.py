#!/usr/bin/env python3
"""Validate the exact-symbol decision projection; no models/providers/writes."""
import argparse
from datetime import datetime, timezone
import json
import os
from urllib.parse import urlencode
from urllib.request import urlopen

from validate_personal_history_real import validate_observed_projection, wait_ready


def validate(body, ticker):
    assert body["match_policy"] == "EXACT_SYMBOL", body
    assert body["ranking_effect"] == "NONE", body
    assert len(body["candidates"]) == 1, body
    assert body["candidates"][0]["subject_id"] == ticker, body
    assert set(body["subjects"]) == {ticker}, body
    history = body["subjects"][ticker]
    assert history["match_policy"] == "EXACT_SYMBOL", history
    validate_observed_projection(history)
    for execution in history["executions"]:
        assert execution["symbol"] == ticker, execution
        assert execution["identity_match"] == "EXACT_SYMBOL", execution
    for sequence in history["observed_sequences"]:
        assert sequence["symbol"] == ticker, sequence
        assert sequence["identity_match"] == "EXACT_SYMBOL", sequence
    return history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("B3_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--ticker", help="Exact stock/option symbol; default uses an already observed symbol")
    parser.add_argument("--ready-timeout", type=float, default=60)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    wait_ready(base, args.ready_timeout)
    ticker = args.ticker.strip().upper() if args.ticker else None
    if not ticker:
        with urlopen(base + "/history/context", timeout=20) as response:
            existing = json.load(response)
        ticker = next((row["symbol"] for row in existing.get("executions", [])), "PETR4")
    for cutoff in (None, datetime.now(timezone.utc).isoformat()):
        params = {"ticker": ticker}
        if cutoff:
            params["as_of"] = cutoff
        with urlopen(base + "/history/decision-context?" + urlencode(params), timeout=20) as response:
            body = json.load(response)
        history = validate(body, ticker)
        if cutoff:
            assert history["mode"] == "STRICT_KNOWN_AT_TIME", history
        print(json.dumps({
            "ticker": ticker, "mode": history["mode"], "status": history["status"],
            "execution_count": history["execution_count"], "observed_sequence_count": history["observed_sequence_count"],
            "eligible_outcome_count": history["historical_admission"]["eligible_outcome_count"],
            "sources": history["sources"], "excluded": history["excluded"],
        }, ensure_ascii=False))
    print("PASS EXACT DECISION HISTORY + STRICT CUTOFF — complete UC-07/08/09 NOT VALIDATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
