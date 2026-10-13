from b3_agent.routing import FastRouter, MatchClass, RouteTarget


def test_price_lookup_routes_to_market_provider():
    d = FastRouter().route("qual o preço de PETR4?")
    assert d.target == RouteTarget.MARKET_PROVIDER
    assert d.use_case == "UC-01"
    assert d.metadata["ticker"] == "PETR4"


def test_options_metrics_routes_deterministically():
    d = FastRouter().route("qual o delta e theta da minha PUT PETR4?")
    assert d.target == RouteTarget.OPTIONS_ENGINE
    assert d.use_case == "UC-02"


def test_explicit_stress_routes_deterministically():
    d = FastRouter().route("rode stress com IBOV -10%")
    assert d.target == RouteTarget.STRESS_ENGINE
    assert d.use_case == "UC-11"


def test_nightly_job_routes_to_deepseek_background():
    d = FastRouter().route(source="scheduler", task_type="b3.news.nightly")
    assert d.target == RouteTarget.DEEPSEEK_BACKGROUND
    assert d.execution_mode == "background"
    assert d.use_case == "UC-10"


def test_complex_strategy_escalates_to_openclaw():
    d = FastRouter().route("compare comprar PETR4 com vender uma PUT")
    assert d.target == RouteTarget.OPENCLAW
    assert d.route == "senior_llm"


def test_ambiguous_input_escalates_safely():
    d = FastRouter().route("o que você acha disso?")
    assert d.target == RouteTarget.OPENCLAW
    assert d.match == MatchClass.AMBIGUOUS


def test_portfolio_dashboard_metadata_routes_exactly():
    d = FastRouter().route(
        "UC-01 Portfolio Intelligence",
        metadata={"dashboard_page": "Portfolio", "use_cases": ["UC-01"]},
    )
    assert d.target == RouteTarget.PORTFOLIO_ENGINE
    assert d.match == MatchClass.MATCH_EXACT


def test_options_dashboard_metadata_routes_exactly():
    d = FastRouter().route(
        "UC-02 Options Position & Lifecycle Intelligence",
        metadata={"dashboard_page": "Options", "use_cases": ["UC-02"]},
    )
    assert d.target == RouteTarget.OPTIONS_ENGINE
    assert d.match == MatchClass.MATCH_EXACT


def test_risk_dashboard_metadata_routes_exactly():
    d = FastRouter().route(
        "UC-11 Risk, Scenario & Stress Intelligence",
        metadata={"dashboard_page": "Risk & Stress", "use_cases": ["UC-11"]},
    )
    assert d.target == RouteTarget.STRESS_ENGINE
    assert d.match == MatchClass.MATCH_EXACT


def test_complex_intent_wins_over_dashboard_metadata():
    d = FastRouter().route(
        "vale a pena vender PETR4 agora?",
        metadata={"dashboard_page": "Portfolio", "use_cases": ["UC-01"]},
    )
    assert d.target == RouteTarget.OPENCLAW


def test_estado_atual_da_carteira_routes_without_dashboard_metadata():
    d = FastRouter().route("Resuma o estado atual da carteira")
    assert d.target == RouteTarget.PORTFOLIO_ENGINE


def test_structured_strategy_lab_stock_comparison_routes_deterministically():
    d = FastRouter().route(
        "UC-04: compare Comprar ação em VALE3 e Comprar ação em WEGE3",
        metadata={
            "workspace": "Strategy Lab",
            "comparison_assets": ["VALE3", "WEGE3"],
            "strategy_a": "Comprar ação",
            "strategy_b": "Comprar ação",
        },
    )
    assert d.target == RouteTarget.STRATEGY_ENGINE
    assert d.use_case == "UC-04"
    assert d.match == MatchClass.MATCH_EXACT


def test_structured_strategy_lab_sell_put_without_contract_still_escalates():
    d = FastRouter().route(
        "UC-04: compare Comprar ação em VALE3 e Vender PUT em WEGE3",
        metadata={
            "workspace": "Strategy Lab",
            "comparison_assets": ["VALE3", "WEGE3"],
            "strategy_a": "Comprar ação",
            "strategy_b": "Vender PUT",
        },
    )
    assert d.target == RouteTarget.OPENCLAW


def test_structured_strategy_lab_sell_put_with_contract_routes_deterministically():
    d = FastRouter().route(
        "UC-04: compare Comprar ação em VALE3 e Vender PUT WEGEV500 em WEGE3",
        metadata={
            "workspace": "Strategy Lab",
            "comparison_assets": ["VALE3", "WEGE3"],
            "strategy_a": "Comprar ação",
            "strategy_b": "Vender PUT",
            "option_b": "WEGEV500",
        },
    )
    assert d.target == RouteTarget.STRATEGY_ENGINE
    assert d.use_case == "UC-04"


def test_structured_strategy_lab_covered_call_with_contract_routes_deterministically():
    d = FastRouter().route(
        "UC-04: compare Manter WEGE3 e Vender CALL coberta WEGEJ550 em WEGE3",
        metadata={
            "workspace": "Strategy Lab",
            "comparison_assets": ["WEGE3", "WEGE3"],
            "strategy_a": "Manter",
            "strategy_b": "Vender CALL coberta",
            "option_b": "WEGEJ550",
        },
    )
    assert d.target == RouteTarget.STRATEGY_ENGINE
    assert d.use_case == "UC-04"


def test_structured_strategy_lab_covered_call_without_contract_escalates():
    d = FastRouter().route(
        "UC-04: compare Manter WEGE3 e Vender CALL coberta em WEGE3",
        metadata={
            "workspace": "Strategy Lab",
            "comparison_assets": ["WEGE3", "WEGE3"],
            "strategy_a": "Manter",
            "strategy_b": "Vender CALL coberta",
        },
    )
    assert d.target == RouteTarget.OPENCLAW


def test_structured_strategy_lab_stock_reduction_routes_deterministically():
    d = FastRouter().route(
        "UC-04: compare Manter WEGE3 e Vender/reduzir ação WEGE3",
        metadata={
            "workspace": "Strategy Lab",
            "comparison_assets": ["WEGE3", "WEGE3"],
            "strategy_a": "Manter",
            "strategy_b": "Vender/reduzir ação",
            "comparison_amount": 2000,
        },
    )
    assert d.target == RouteTarget.STRATEGY_ENGINE
    assert d.use_case == "UC-04"


def test_structured_stock_reduction_without_amount_escalates():
    d = FastRouter().route(
        "UC-04: compare Manter WEGE3 e Vender/reduzir ação WEGE3",
        metadata={
            "workspace": "Strategy Lab",
            "comparison_assets": ["WEGE3", "WEGE3"],
            "strategy_a": "Manter",
            "strategy_b": "Vender/reduzir ação",
        },
    )
    assert d.target == RouteTarget.OPENCLAW
