from __future__ import annotations

from typing import Any

from b3_agent.routing.models import MatchClass, RouteDecision, RouteTarget


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
        meta.setdefault("source", source)

        ticker = self._extract_ticker(raw)
        if ticker:
            meta.setdefault("ticker", ticker)

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

        # Structured Strategy Lab requests use the deterministic UC-04 composer
        # before any senior-LLM escalation. Unsupported strategy types continue
        # to OpenClaw until their deterministic builders are implemented.
        workspace = str(meta.get("workspace") or meta.get("dashboard_page") or "").strip().lower()
        comparison_assets = meta.get("comparison_assets")
        strategy_a = str(meta.get("strategy_a") or "").strip()
        strategy_b = str(meta.get("strategy_b") or "").strip()
        option_a = str(meta.get("option_a") or "").strip() or None
        option_b = str(meta.get("option_b") or "").strip() or None
        comparison_amount = meta.get("comparison_amount")
        stock_reduction_present = (
            self._is_stock_reduction(strategy_a)
            or self._is_stock_reduction(strategy_b)
        )
        stock_reduction_amount_ok = (
            not stock_reduction_present
            or self._positive_number(comparison_amount)
        )
        if (
            workspace == "strategy lab"
            and isinstance(comparison_assets, (list, tuple))
            and len(comparison_assets) == 2
            and self._strategy_supported(strategy_a, option_a)
            and self._strategy_supported(strategy_b, option_b)
            and stock_reduction_amount_ok
        ):
            return self._decision(
                "strategy_comparison", "UC-04", "sync", "deterministic",
                RouteTarget.STRATEGY_ENGINE, MatchClass.MATCH_EXACT,
                "B3_STRATEGY_COMPARISON_V1", meta,
            )

        # Explicitly complex intent always wins over dashboard metadata.
        if self._contains_any(
            normalized,
            (
                "compare",
                "comparar",
                "melhor estratégia",
                "melhor estrategia",
                "roll",
                "tese",
                "vale a pena",
            ),
        ):
            return self._decision(
                "complex_analysis", None, "sync", "senior_llm",
                RouteTarget.OPENCLAW, MatchClass.MATCH_STRONG,
                "B3_COMPLEX_ANALYSIS_V1", meta,
            )

        if self._contains_any(normalized, ("preço", "preco", "cotação", "cotacao", "quote")) and meta.get("ticker"):
            return self._decision(
                "market_price_lookup", "UC-01", "sync", "deterministic",
                RouteTarget.MARKET_PROVIDER, MatchClass.MATCH_STRONG,
                "B3_MARKET_PRICE_V1", meta,
            )

        if self._contains_any(normalized, ("carteira", "portfolio", "portfólio")) and self._contains_any(
            normalized,
            (
                "como está",
                "como esta",
                "estado atual",
                "resuma",
                "resumo",
                "snapshot",
                "posição",
                "posicao",
                "posições",
                "posicoes",
                "concentração",
                "concentracao",
            ),
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

        if self._contains_any(normalized, ("stress", "cenário", "cenario")) and self._has_percentage(normalized):
            return self._decision(
                "stress_scenario", "UC-11", "sync", "deterministic",
                RouteTarget.STRESS_ENGINE, MatchClass.MATCH_STRONG,
                "B3_STRESS_SCENARIO_V1", meta,
            )

        # React/Tauri sends canonical page/use-case metadata. Use it only after
        # checking explicit user intent so a complex question can still
        # escalate to senior reasoning.
        dashboard_page = str(meta.get("dashboard_page") or "").strip().lower()
        use_cases = self._use_cases(meta.get("use_cases"))

        if dashboard_page == "portfolio" and use_cases == ("UC-01",):
            return self._decision(
                "portfolio_snapshot", "UC-01", "sync", "deterministic",
                RouteTarget.PORTFOLIO_ENGINE, MatchClass.MATCH_EXACT,
                "B3_DASHBOARD_UC01_V1", meta,
            )

        if dashboard_page == "options" and use_cases == ("UC-02",):
            return self._decision(
                "options_positions", "UC-02", "sync", "deterministic",
                RouteTarget.OPTIONS_ENGINE, MatchClass.MATCH_EXACT,
                "B3_DASHBOARD_UC02_V1", meta,
            )

        if dashboard_page == "risk & stress" and use_cases == ("UC-11",):
            return self._decision(
                "risk_stress_snapshot", "UC-11", "sync", "deterministic",
                RouteTarget.STRESS_ENGINE, MatchClass.MATCH_EXACT,
                "B3_DASHBOARD_UC11_V1", meta,
            )

        return self._decision(
            None, None, "sync", "senior_llm", RouteTarget.OPENCLAW,
            MatchClass.AMBIGUOUS, None, meta,
        )

    @staticmethod
    def _is_stock_reduction(value: str) -> bool:
        normalized = " ".join(value.casefold().split())
        return normalized in {
            "vender ação",
            "vender acao",
            "vender/reduzir ação",
            "vender/reduzir acao",
            "reduzir ação",
            "reduzir acao",
            "sell stock",
            "sell_stock",
            "reduce stock",
            "reduce_stock",
        }

    @staticmethod
    def _positive_number(value: object) -> bool:
        try:
            return float(value) > 0
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _strategy_supported(value: str, option_id: str | None = None) -> bool:
        normalized = " ".join(value.casefold().split())
        if normalized in {
            "comprar ação",
            "comprar acao",
            "buy stock",
            "buy_stock",
            "manter",
            "hold",
            "vender ação",
            "vender acao",
            "vender/reduzir ação",
            "vender/reduzir acao",
            "reduzir ação",
            "reduzir acao",
            "sell stock",
            "sell_stock",
            "reduce stock",
            "reduce_stock",
        }:
            return True
        if normalized in {
            "vender put",
            "sell put",
            "sell_put",
            "vender call",
            "vender call coberta",
            "covered call",
            "sell call",
            "sell_call",
        }:
            return bool(str(option_id or "").strip())
        return False

    @staticmethod
    def _contains_any(text: str, values: tuple[str, ...]) -> bool:
        return any(value in text for value in values)

    @staticmethod
    def _use_cases(value: Any) -> tuple[str, ...]:
        if not isinstance(value, (list, tuple)):
            return ()
        return tuple(str(item).upper().strip() for item in value if str(item).strip())

    @staticmethod
    def _extract_ticker(text: str) -> str | None:
        cleaned = "".join(ch if ch.isalnum() else " " for ch in text.upper())
        for token in cleaned.split():
            if len(token) not in {5, 6}:
                continue
            letters = token[:4]
            digits = token[4:]
            if letters.isalpha() and digits.isdigit():
                return token
        return None

    @staticmethod
    def _has_percentage(text: str) -> bool:
        return "%" in text and any(ch.isdigit() for ch in text)

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
