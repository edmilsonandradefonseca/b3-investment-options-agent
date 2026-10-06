"""Decision-ready BUY pair projection from existing evidence, without forecasts."""
from datetime import datetime
from zoneinfo import ZoneInfo
import math


def _number(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _timestamp(value):
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None



def _common_normalized_history(packs, cutoff):
    histories = []
    adjusted = True
    for pack in packs:
        admitted = {}
        for row in pack.market.get("price_history", []):
            at = _timestamp(row.get("observation_timestamp"))
            available = _timestamp(row.get("available_timestamp"))
            price = _number(row.get("close"))
            if not at or not available or at > cutoff or available > cutoff or not price or price <= 0:
                continue
            day = at.astimezone(ZoneInfo("America/Sao_Paulo")).date().isoformat()
            if day in admitted:
                # Ambiguous duplicated sessions cannot establish a common index.
                return {"status": "AMBIGUOUS_SESSION", "rows": []}
            admitted[day] = row
            value = _number(row.get("adjusted_close"))
            adjusted = adjusted and value is not None and value > 0
        histories.append(admitted)
    common = sorted(set(histories[0]) & set(histories[1]))
    if len(common) < 2:
        return {"status": "INSUFFICIENT_COMMON_HISTORY", "rows": []}
    field = "adjusted_close" if adjusted else "close"
    bases = [history[common[0]][field] for history in histories]
    rows = [{"date": day, "left_index": histories[0][day][field] / bases[0] * 100,
             "right_index": histories[1][day][field] / bases[1] * 100}
            for day in common]
    return {"status": "AVAILABLE", "base": 100, "price_basis": field,
            "left_ticker": packs[0].ticker, "right_ticker": packs[1].ticker,
            "start_date": common[0], "end_date": common[-1], "rows": rows}


def stock_purchase_payload(alternatives, packs, cutoff, dividend_evidence=None, target_evidence=None, portfolio=None, economic_inputs=None):
    rows = []
    cutoff_local_date = cutoff.astimezone(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    for alternative, pack in zip(alternatives, packs, strict=True):
        quote = pack.market.get("current_quote") or {}
        observed = _timestamp(quote.get("observation_timestamp"))
        available = _timestamp(quote.get("available_timestamp"))
        spot = _number(quote.get("close"))
        if (spot is None or spot <= 0 or not observed or not available
                or observed > cutoff or available > cutoff
                or (cutoff - observed).total_seconds() > 7 * 86400
                or quote.get("quality_status") == "REJECTED"):
            spot = None
        admitted, excluded = {}, []
        for name, raw in pack.fundamentals.get("metrics", {}).items():
            metric = dict(raw)
            at = _timestamp(metric.get("available_timestamp"))
            report = str(metric.get("report_date") or "")[:10]
            current_snapshot = metric.get("period_type") == "CURRENT_SNAPSHOT"
            if (not at or at > cutoff or (not report and not current_snapshot) or report > cutoff_local_date
                    or metric.get("quality_status") == "REJECTED"
                    or not metric.get("source") or _number(metric.get("value")) is None):
                excluded.append({"metric": name, "report_date": report or None, "available_timestamp": metric.get("available_timestamp"), "reason": "UNQUALIFIED_OR_FUTURE_FUNDAMENTAL"})
                continue
            admitted[name] = metric
        from b3_agent.dividend_evidence import dividend_payload
        dividends = dividend_payload(pack.ticker, (dividend_evidence or {}).get(pack.ticker, {}), cutoff)
        rows.append({
            "alternative_id": alternative.alternative_id, "ticker": pack.ticker,
            "current_price_brl": spot, "quote_observed_at": observed,
            "capital_required_brl": alternative.capital_required,
            "fundamental_metrics": admitted, "excluded_metrics": excluded,
            "dividends": dividends,
            "institution_targets": (target_evidence or {}).get(pack.ticker, {"status":"UNKNOWN_NO_ADMISSIBLE_TARGETS", "rows":[]}),
            "observed_risk": {name: pack.quant.get(name) for name in
                ("volatility_60d", "max_drawdown", "average_dollar_volume_20d")},
            "history_start": pack.market.get("history_start"),
            "history_end": pack.market.get("history_end"),
            "historical_returns": pack.market.get("historical_returns", {}),
            "history_count": pack.market.get("history_count"),
            "portfolio": pack.portfolio, "source_refs": list(pack.source_refs),
            "evidence_refs": list(alternative.evidence_refs),
            "expected_return": None, "positive_return_probability": None,
            "future_dividend_per_share": None, "verified_price_target": None,
            "forecast_status": "UNKNOWN_NO_QUALIFIED_FORECAST_EVIDENCE",
        })
    from b3_agent.economic_evidence import economic_evidence
    for row in rows:
        row["economic_evidence"] = economic_evidence(row, budget=row["capital_required_brl"],
            entry_cost=(economic_inputs or {}).get("entry_costs_brl",{}).get(row["ticker"]), portfolio=portfolio)
    comparisons = []
    for name in sorted(set(rows[0]["fundamental_metrics"]) | set(rows[1]["fundamental_metrics"])):
        left = rows[0]["fundamental_metrics"].get(name)
        right = rows[1]["fundamental_metrics"].get(name)
        comparable = bool(left and right and left.get("unit") is not None
            and left.get("unit") == right.get("unit")
            and left.get("report_date") is not None
            and left["report_date"] == right["report_date"]
            and left.get("period_type") is not None
            and left.get("period_type") != "CURRENT_SNAPSHOT"
            and left.get("period_type") == right.get("period_type"))
        comparisons.append({"metric": name, "status": "COMPARABLE" if comparable else "NONCOMPARABLE_OR_MISSING",
            "right_minus_left": right["value"] - left["value"] if comparable else None})
    historical_comparisons = []
    for period in ("1W", "1M", "3M", "6M", "1Y"):
        left = rows[0]["historical_returns"].get(period, {})
        right = rows[1]["historical_returns"].get(period, {})
        same_dates = bool(
            left.get("status") == right.get("status") == "AVAILABLE"
            and str(left.get("start_at"))[:10] == str(right.get("start_at"))[:10]
            and str(left.get("end_at"))[:10] == str(right.get("end_at"))[:10]
        )
        historical_comparisons.append({
            "period": period,
            "status": "COMPARABLE" if same_dates else "INSUFFICIENT_OR_DIFFERENT_DATES",
            "right_minus_left_return_fraction": (
                right["return_fraction"] - left["return_fraction"] if same_dates else None
            ),
        })
    same_window = bool(rows[0]["history_start"] and rows[0]["history_end"]
        and rows[0]["history_start"] == rows[1]["history_start"]
        and rows[0]["history_end"] == rows[1]["history_end"])
    return {"policy_version": "stock-buy-evidence-v1", "rows": rows,
        "common_normalized_history": _common_normalized_history(packs, cutoff),
        "fundamental_comparisons": comparisons, "historical_comparisons": historical_comparisons, "observed_risk_same_window": same_window,
        "ranking": "UNKNOWN_NO_QUALIFIED_RETURN_OR_DIVIDEND_FORECAST",
        "limitations": [
            "Observed fundamentals are not future dividends, verified price targets or expected return.",
            "Fundamental differences require equal report dates, period types and explicit units; they do not select an investment winner.",
            "Historical risk is descriptive; differing windows cannot establish a comparative risk rank.",
            "Dividend forecasts, entitlement dates, calibrated return probabilities and institution-sourced targets require separate qualified evidence.",
        ]}
