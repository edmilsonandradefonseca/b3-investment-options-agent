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
