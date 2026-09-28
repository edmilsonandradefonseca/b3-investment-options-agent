from __future__ import annotations

import re
from typing import Any

from b3_agent.routing.models import MatchClass, RouteDecision, RouteTarget

_TICKER_RE = re.compile(r"\\b([A-Z]{4}[0-9]{1,2})\\b", re.IGNORECASE)


class FastRouter:
    """Deterministic V4.1 router. Unknown or ambiguous input escalates safely."""

    def route(
        self,
        text: str = "",
        *,
        source: str = "user",
        task_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RouteDecision:
        raw = (text or "").strip()
        normalized = " ".join(raw.lower().split())
        meta = dict(metadata or {})
        ticker_match = _TICKER_RE.search(raw.upper())
        if ticker_match:
            meta.setdefault("ticker", ticker_match.group(1).upper())

        if task_type in {"b3.news.nightly", "b3.research.nightly", "nightly_ticker_intelligence"}:
            return self._decision(
                "nightly_ticker_intelligence", "UC-10", "background",
                "local_reasoning", RouteTarget.DEEPSEEK_BACKGROUND,
                MatchClass.MATCH_EXACT, "B3_NIGHTLY_RESEARCH_V1", meta,
            )

        if task_type == "macro_refresh":
            return self._decision(
                "macro_refresh", "UC-05", "background", "deterministic",
                RouteTarget.MACRO_JOB, MatchClass.MATCH_EXACT,
                "B3_MACRO_REFRESH_V1", meta,
            )

        if self._contains_any(normalized, ("preço", "preco", "cotação", "cotacao", "quote")) and meta.get("ticker"):
            return self._decision(
                "market_price_lookup", "UC-01", "sync", "deterministic",
                RouteTarget.MARKET_PROVIDER, MatchClass.MATCH_STRONG,
                "B3_MARKET_PRICE_V1", meta,
            )

        if self._contains_any(normalized, ("carteira", "portfolio", "portfólio")) and self._contains_any(
            normalized, ("como está", "como esta", "snapshot", "posição", "posicao", "concentração", "concentracao")
        ):
            return self._decision(
                "portfolio_snapshot", "UC-01", "sync", "deterministic",
                RouteTarget.PORTFOLIO_ENGINE, MatchClass.MATCH_STRONG,
                "B3_PORTFOLIO_SNAPSHOT_V1", meta,
            )

        if self._contains_any(normalized, ("greek", "delta", "gamma", "theta", "vega", "dte", "moneyness")):
            return self._decision(
                "options_metrics", "UC-02", "sync", "deterministic",
                RouteTarget.OPTIONS_ENGINE, MatchClass.MATCH_STRONG,
                "B3_OPTIONS_METRICS_V1", meta,
            )

        if self._contains_any(normalized, ("stress", "cenário", "cenario")) and re.search(r"[-+]?\\d+(?:[.,]\\d+)?\\s*%", normalized):
            return self._decision(
                "stress_scenario", "UC-11", "sync", "deterministic",
                RouteTarget.STRESS_ENGINE, MatchClass.MATCH_STRONG,
                "B3_STRESS_SCENARIO_V1", meta,
            )

        if self._contains_any(normalized, ("compare", "comparar", "melhor estratégia", "melhor estrategia", "roll", "tese", "vale a pena")):
            return self._decision(
                "complex_analysis", None, "sync", "senior_llm",
                RouteTarget.OPENCLAW, MatchClass.MATCH_STRONG,
                "B3_COMPLEX_ANALYSIS_V1", meta,
            )

        return self._decision(
            None, None, "sync", "senior_llm", RouteTarget.OPENCLAW,
            MatchClass.AMBIGUOUS, None, meta,
        )

    @staticmethod
    def _contains_any(text: str, values: tuple[str, ...]) -> bool:
        return any(value in text for value in values)

    @staticmethod
    def _decision(
        intent: str | None,
        use_case: str | None,
        execution_mode: str,
        route: str,
        target: RouteTarget,
        match: MatchClass,
        matched_rule: str | None,
        metadata: dict[str, Any],
    ) -> RouteDecision:
        return RouteDecision(
            namespace="b3",
            intent=intent,
            use_case=use_case,
            execution_mode=execution_mode,
            route=route,
            target=target,
            match=match,
            matched_rule=matched_rule,
            metadata=metadata,
        )
