"""Versioned, source-qualified stock opportunity materiality screen.

An admitted institutional target is only a conditional price opinion. This policy
selects items for human review; it never emits a BUY, expected return, or probability.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

POLICY_VERSION = "B3_STOCK_MATERIALITY_TARGET_REVIEW_V1"
MIN_PRICE_ONLY_UPSIDE = 0.15
MAX_QUOTE_AGE_DAYS = 7


def _aware(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def classify_stock_materiality(row: dict[str, Any], as_of: datetime) -> dict[str, Any]:
    """Classify one analyzed stock into a material review item, monitor, or gap."""
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    ticker = str(row.get("ticker") or "")
    quote_at = _aware(row.get("quote_as_of"))
    quote_age_days = (as_of.astimezone(timezone.utc) - quote_at).total_seconds() / 86400 if quote_at else None
    spot = row.get("current_price")
    quote_usable = (
        isinstance(spot, (int, float))
        and not isinstance(spot, bool)
        and spot > 0
        and quote_age_days is not None
        and 0 <= quote_age_days <= MAX_QUOTE_AGE_DAYS
    )
    target_bundle = row.get("institution_targets") or {}
    target_status = str(target_bundle.get("status") or "UNKNOWN")
    targets = row.get("economic_evidence", {}).get("institution_target_potential", [])
    positives = []
    for target in targets if isinstance(targets, list) else []:
        upside = target.get("price_only_upside_fraction")
        if isinstance(upside, (int, float)) and not isinstance(upside, bool):
            positives.append({**target, "price_only_upside_fraction": float(upside)})

    base = {
        "ticker": ticker,
        "policy_version": POLICY_VERSION,
        "status": "MONITOR",
        "category": "ACOMPANHAR",
        "conditional_price_only_upside_fraction": None,
        "why_now": None,
        "evidence_refs": [],
        "target_horizon": None,
        "quote_as_of": row.get("quote_as_of"),
        "quote_age_days": round(quote_age_days, 2) if quote_age_days is not None else None,
        "risk_context": {
            "volatility_60d": row.get("volatility_60d"),
            "max_drawdown": row.get("max_drawdown"),
            "liquidity_proxy_20d": row.get("liquidity_proxy_20d"),
        },
        "portfolio_context": {
            "held": (row.get("portfolio") or {}).get("held"),
            "stock_quantity": (row.get("portfolio") or {}).get("stock_quantity"),
            "open_option_count": (row.get("portfolio") or {}).get("open_option_count"),
            "snapshot_as_of": (row.get("portfolio") or {}).get("snapshot_as_of"),
        },
        "reason": "",
        "recheck_when": "Atualizar quando houver nova cotação recente ou relatório primário qualificado.",
    }
    if not quote_usable:
        base.update(
            status="INCOMPLETE",
            category="EVIDENCIA_INSUFICIENTE",
            reason="Cotação ausente, inválida ou com mais de sete dias; não é possível calcular potencial condicional atual.",
        )
        return base

    material_targets = [
        target for target in positives
        if target["price_only_upside_fraction"] >= MIN_PRICE_ONLY_UPSIDE
    ]
    if material_targets:
        # Each row was independently admitted by StoredPriceTargetService. Keep
        # house, horizon, publication date and source attached; do not pool reports.
        chosen = max(
            material_targets,
            key=lambda item: (item["price_only_upside_fraction"], str(item.get("published_at") or "")),
        )
        held = (row.get("portfolio") or {}).get("held")
        base.update(
            status="MATERIAL_REVIEW",
            category="REVISAR_EXPOSICAO" if held is True else "POTENCIAL_ENTRADA_PARA_REVISAO",
            conditional_price_only_upside_fraction=chosen["price_only_upside_fraction"],
            why_now=(
                f"{chosen.get('institution', 'Instituição')} publicou alvo de "
                f"R$ {chosen.get('price_brl'):.2f} para {chosen.get('horizon_date')}; "
                f"isso implica potencial condicional de "
                f"{chosen['price_only_upside_fraction']:.1%} frente à cotação observada. "
                "É uma opinião de preço, não retorno esperado nem recomendação."
            ),
            evidence_refs=[chosen.get("source_url")] if chosen.get("source_url") else [],
            target_horizon=str(chosen.get("horizon_date")) if chosen.get("horizon_date") else None,
            reason=(
                f"Alvo primário qualificado supera o limiar versionado de "
                f"{MIN_PRICE_ONLY_UPSIDE:.0%}. A decisão continua condicionada a risco, "
                "fundamentos, eventos, carteira e contrapontos da síntese B3."
            ),
        )
        return base

    unavailable = target_status in {"STORE_UNAVAILABLE", "ERROR", "FAILED"}
    if unavailable:
        base.update(
            status="INCOMPLETE",
            category="EVIDENCIA_INSUFICIENTE",
            reason="A consulta à fonte de alvos institucionais falhou; nenhum resultado vazio foi interpretado como ausência de oportunidade.",
        )
    elif positives:
        best = max(positives, key=lambda item: item["price_only_upside_fraction"])
        base.update(
            conditional_price_only_upside_fraction=best["price_only_upside_fraction"],
            evidence_refs=[best.get("source_url")] if best.get("source_url") else [],
            target_horizon=str(best.get("horizon_date")) if best.get("horizon_date") else None,
            reason=(
                f"O maior potencial condicional admitido foi {best['price_only_upside_fraction']:.1%}, "
                f"abaixo do limiar de revisão de {MIN_PRICE_ONLY_UPSIDE:.0%}; permanece em acompanhamento."
            ),
        )
    else:
        base["reason"] = (
            "Nenhum alvo institucional primário admissível atingiu o critério de revisão. "
            f"Estado da fonte: {target_status}. Isso não prova ausência de catalisadores fora desta evidência."
        )
    return base


OPPORTUNITY_RESEARCH_BUDGET_POLICY = "B3_OPPORTUNITY_RESEARCH_ENRICHMENT_V1"
MAX_SYNCHRONOUS_RESEARCH_TICKERS = 8


def build_opportunity_research_scope(
    screen: dict[str, Any],
    requested_tickers: list[str] | tuple[str, ...],
    *,
    limit: int = MAX_SYNCHRONOUS_RESEARCH_TICKERS,
) -> dict[str, Any]:
    """Bound optional synchronous news enrichment without truncating screening.

    All names remain in the deterministic screen. Explicitly watched stocks and
    material review candidates receive first priority for the slower research
    context; the returned counts make omitted enrichment visible.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    rows = screen.get("rows") if isinstance(screen.get("rows"), list) else []
    eligible = [
        str(row.get("ticker") or "").strip().upper()
        for row in rows
        if isinstance(row, dict)
        and row.get("discovery_eligible") is True
        and str(row.get("ticker") or "").strip()
    ]
    if not eligible:
        eligible = [
            str(ticker).strip().upper()
            for ticker in requested_tickers
            if isinstance(ticker, str) and ticker.strip()
        ]
    eligible = list(dict.fromkeys(eligible))
    eligible_set = set(eligible)

    def symbols(values: Any) -> list[str]:
        return list(dict.fromkeys(
            str(item).strip().upper()
            for item in values if isinstance(item, str) and item.strip()
        )) if isinstance(values, (list, tuple)) else []

    material_rows = screen.get("material_candidates")
    material = [
        str(item.get("ticker") or "").strip().upper()
        for item in material_rows if isinstance(item, dict) and item.get("ticker")
    ] if isinstance(material_rows, list) else []
    priorities = (
        symbols(screen.get("candidate_universe"))
        + material
        + symbols(screen.get("portfolio_stock_universe"))
        + eligible
    )
    ordered = list(dict.fromkeys(ticker for ticker in priorities if ticker in eligible_set))
    selected = ordered[:limit]
    return {
        "policy_version": OPPORTUNITY_RESEARCH_BUDGET_POLICY,
        "status": "COMPLETE" if len(eligible) <= len(selected) else "PARTIAL",
        "screened_stock_count": len(eligible),
        "contextual_research_count": len(selected),
        "deterministic_only_count": len(eligible) - len(selected),
        "option_underlying_context_count": max(
            0,
            len(screen.get("requested_universe", [])) - len(eligible),
        ),
        "context_tickers": selected,
        "deterministic_only_reason": (
            "Synchronous news enrichment budget reached; deterministic screening, "
            "quotes, portfolio exposure and materiality remain available for every stock."
            if len(eligible) > len(selected)
            else None
        ),
    }
