"""Decision-ready BUY pair projection from existing evidence, without forecasts."""
from datetime import datetime
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


def stock_purchase_payload(alternatives, packs, cutoff, dividend_evidence=None):
    rows = []
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
            if (not at or at > cutoff or not report or report > cutoff.date().isoformat()
                    or metric.get("quality_status") == "REJECTED"
                    or not metric.get("source") or _number(metric.get("value")) is None):
                excluded.append({"metric": name, "reason": "UNQUALIFIED_OR_FUTURE_FUNDAMENTAL"})
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
            "observed_risk": {name: pack.quant.get(name) for name in
                ("volatility_60d", "max_drawdown", "average_dollar_volume_20d")},
            "history_start": pack.market.get("history_start"),
            "history_end": pack.market.get("history_end"),
            "portfolio": pack.portfolio, "source_refs": list(pack.source_refs),
            "evidence_refs": list(alternative.evidence_refs),
            "expected_return": None, "positive_return_probability": None,
            "future_dividend_per_share": None, "verified_price_target": None,
            "forecast_status": "UNKNOWN_NO_QUALIFIED_FORECAST_EVIDENCE",
        })
    comparisons = []
    for name in sorted(set(rows[0]["fundamental_metrics"]) | set(rows[1]["fundamental_metrics"])):
        left = rows[0]["fundamental_metrics"].get(name)
        right = rows[1]["fundamental_metrics"].get(name)
        comparable = bool(left and right and left.get("unit") is not None
            and left.get("unit") == right.get("unit")
            and left["report_date"] == right["report_date"]
            and left.get("period_type") is not None
            and left.get("period_type") == right.get("period_type"))
        comparisons.append({"metric": name, "status": "COMPARABLE" if comparable else "NONCOMPARABLE_OR_MISSING",
            "right_minus_left": right["value"] - left["value"] if comparable else None})
    same_window = bool(rows[0]["history_start"] and rows[0]["history_end"]
        and rows[0]["history_start"] == rows[1]["history_start"]
        and rows[0]["history_end"] == rows[1]["history_end"])
    return {"policy_version": "stock-buy-evidence-v1", "rows": rows,
        "fundamental_comparisons": comparisons, "observed_risk_same_window": same_window,
        "ranking": "UNKNOWN_NO_QUALIFIED_RETURN_OR_DIVIDEND_FORECAST",
        "limitations": [
            "Observed fundamentals are not future dividends, verified price targets or expected return.",
            "Fundamental differences require equal report dates, period types and explicit units; they do not select an investment winner.",
            "Historical risk is descriptive; differing windows cannot establish a comparative risk rank.",
            "Dividend forecasts, entitlement dates, calibrated return probabilities and institution-sourced targets require separate qualified evidence.",
        ]}
