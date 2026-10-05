#!/usr/bin/env python3
"""Real Ubuntu conditional stock screen; metadata only in public Actions logs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from time import monotonic


def _failure_category(status, data):
    detail = data.get('detail') or data.get('error') or ''
    if isinstance(detail, (dict, list)):
        detail = json.dumps(detail, ensure_ascii=False)
    text = str(detail).casefold()
    if 'invalid b3 equity ticker' in text:
        return 'INVALID_EQUITY_SYMBOL'
    if 'unsupported opportunity objective' in text:
        return 'UNSUPPORTED_SCREEN_OBJECTIVE'
    if 'select at least one candidate asset' in text:
        return 'EMPTY_SCREEN_UNIVERSE'
    if 'portfolio' in text or 'snapshot' in text or 'position' in text:
        return 'PORTFOLIO_OR_SNAPSHOT'
    if any(token in text for token in ('yahoo', 'oplab', 'brapi', 'provider', 'quote', 'history', 'market data')):
        return 'MARKET_DATA_OR_PROVIDER'
    if any(token in text for token in ('ticker', 'symbol', 'objective', 'asset', 'request', 'unsupported')):
        return 'REQUEST_OR_DOMAIN_VALIDATION'
    if status in (401, 403):
        return 'AUTHORIZATION'
    if status == 422:
        return 'HTTP_CONTRACT_VALIDATION'
    if status == 429:
        return 'RATE_LIMIT'
    if status == 503:
        return 'DEPENDENCY_UNAVAILABLE'
    if status >= 500:
        return 'SERVER_FAILURE'
    return 'API_REJECTION'


def _safe_symbol_profile(data):
    """Describe malformed equity identity without logging the held symbol."""
    detail = data.get('detail') or data.get('error') or ''
    if isinstance(detail, (dict, list)):
        detail = json.dumps(detail, ensure_ascii=False)
    match = __import__('re').search(r"invalid B3 equity ticker ['\\\"]([^'\\\"]+)['\\\"]", str(detail), __import__('re').I)
    if not match:
        return None
    symbol = match.group(1).strip().upper()
    shape = ''.join('L' if char.isalpha() else 'D' if char.isdigit() else 'X' for char in symbol)
    return {'length':len(symbol),'shape':shape,'has_outer_whitespace':symbol != match.group(1).upper(),
            'has_fractional_suffix':symbol.endswith('F') and len(symbol) > 5}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--senior',action='store_true')
    args=parser.parse_args()
    pid=subprocess.check_output(['systemctl','show','b3-runtime.service','--property=MainPID','--value'],text=True,timeout=10).strip()
    assert pid.isdecimal() and int(pid)>0
    for field in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0'):
        key,sep,value=field.partition(b'=')
        name=key.decode('utf-8')
        if sep and (name.startswith('B3_') or name in {'OPLAB_API_TOKEN','BRAPI_TOKEN'}):
            os.environ[name]=value.decode('utf-8')
    os.environ['B3_AGENT_DATA_DIR']='/opt/b3-runtime/data'
    os.environ['B3_AGENT_PROJECT_ROOT']=str(Path(__file__).resolve().parents[1])
    from fastapi.testclient import TestClient
    from b3_agent.server import app
    from validate_live_workspace_outputs import write_private_report
    from b3_agent.config import settings
    from b3_agent.portfolio.snapshot import load_active_snapshots
    client=TestClient(app)
    assets=['VALE3','RENT3','VIVT3','BBAS3']
    portfolio=load_active_snapshots(settings.data_dir).get('portfolio_context')
    if portfolio is None:
        raise AssertionError('Current portfolio snapshot unavailable for Opportunities acceptance')
    stock_positions=[p for p in portfolio.positions if p.instrument_type.upper()=='STOCK']
    option_positions=[p for p in portfolio.positions if p.instrument_type.upper()=='OPTION']
    from b3_agent.strategy_live import _validated_equity_ticker
    expected_stock_tickers=set()
    unresolved_stock_count=0
    for position in stock_positions:
        try:
            expected_stock_tickers.add(_validated_equity_ticker(position.ticker))
        except (TypeError, ValueError):
            unresolved_stock_count += 1
    expected_option_underlyings=set()
    joined_option_count=0
    unresolved_option_count=0
    for position in option_positions:
        try:
            if not position.underlying_ticker:
                raise ValueError('missing option underlying')
            expected_option_underlyings.add(_validated_equity_ticker(position.underlying_ticker))
            joined_option_count += 1
        except (TypeError, ValueError):
            unresolved_option_count += 1
    unresolved_position_count=unresolved_stock_count+unresolved_option_count
    expected_union=set(assets)|expected_stock_tickers|expected_option_underlyings
    for index,objective in enumerate(('LOWEST_REALIZED_VOLATILITY_60D','HIGHEST_OBSERVED_LIQUIDITY_20D')):
        include_portfolio=index==0
        started=monotonic()
        request={'task':'Compare watched assets and the full current stock portfolio by the observed objective; include owned options only as exposure context; never infer valuation or future return.', 'ticker':None,'context':{'workspace':'Opportunities','opportunity_assets':assets,'opportunity_objective':objective,'include_portfolio_stocks':include_portfolio,'analysis_mode':'deterministic','research_mode':'stored_only'}}
        response=client.post('/orchestrate',json=request)
        try:
            data=response.json()
        except ValueError:
            data={'_non_json_response':True}
        if response.status_code != 200 or data.get('error'):
            category=_failure_category(response.status_code,data)
            write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/stock-screen/diagnostics',{
                'instance':'candidate ASGI with real production inputs',
                'objective':objective,
                'http_status':response.status_code,
                'request':request,
                'response':data,
            })
            print(json.dumps({'case':'stock_screen','status':'FAIL','objective':objective,
                'http_status':response.status_code,'error_category':category,
                'detail_present':bool(data.get('detail') or data.get('error')),
                'safe_symbol_profile':_safe_symbol_profile(data)}),flush=True)
            raise AssertionError(f'Opportunities API rejected real screen: HTTP {response.status_code}; {category}')
        result=data['result']; screen=result['opportunity_screen']
        assert result['telemetry']['llm_calls']==0
        assert screen['candidate_universe']==assets
        assert set(result['asset_evidence'])==set(screen['requested_universe'])
        assert len(screen['rows'])==len(screen['requested_universe'])
        assert len(screen['requested_universe'])==len(set(screen['requested_universe']))
        if include_portfolio:
            assert set(screen['requested_universe'])==expected_union, 'Candidate/portfolio/option-underlying union was truncated or incomplete'
            expected_scope_status='PARTIAL' if unresolved_position_count else 'INCLUDED'
            assert screen['portfolio_scope']['status']==expected_scope_status
            assert screen['portfolio_scope']['unresolved_identity_position_count']==unresolved_position_count
            assert screen['portfolio_scope']['unresolved_stock_position_count']==unresolved_stock_count
            assert screen['portfolio_scope']['unresolved_option_underlying_count']==unresolved_option_count
            assert set(screen['portfolio_stock_universe'])==expected_stock_tickers
            assert set(screen['portfolio_option_underlying_universe'])==expected_option_underlyings
            observed_option_count=sum(row['portfolio']['open_option_count'] or 0 for row in screen['rows'])
            assert observed_option_count==joined_option_count, 'Open option positions were not joined to their underlyings'
            context_only=[row for row in screen['rows'] if row['scope_role']=='OPTION_UNDERLYING_CONTEXT']
            assert all(not row['discovery_eligible'] and row['rank'] is None for row in context_only)
        else:
            assert len(screen['rows'])==4
        assert screen['ranked_count']>=2, 'Real provider data did not yield two comparable assets'
        assert all(row['expected_return'] is None for row in screen['rows'])
        print(json.dumps({'case':'stock_screen','objective':objective,'status':screen['status'],'elapsed_ms':round((monotonic()-started)*1000,1),'candidate_count':len(screen['candidate_universe']),'portfolio_stock_count':len(screen['portfolio_stock_universe']),'option_position_count':screen['portfolio_scope']['option_position_count'],'option_underlying_context_count':len(screen['portfolio_option_underlying_universe']),'requested_universe_count':len(screen['requested_universe']),'ranked_count':screen['ranked_count'],'llm_calls':0,'real_portfolio_union':'PASS' if include_portfolio else 'NOT_REQUESTED'}),flush=True)
        write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/stock-screen'/objective,{'instance':'candidate ASGI with real production inputs','request':request,'response':data})
    long_position=next((position for position in portfolio.positions if position.instrument_type.upper()=='STOCK' and position.quantity>=1), None)
    assert long_position is not None, 'No admissible long stock position for funded switch acceptance'
    sell=long_position.ticker
    buy='BBAS3' if sell!='BBAS3' else 'ITUB4'
    funded_request={'task':'Model one-share financing with explicitly hypothetical zero costs; no execution or investment winner.', 'context':{'workspace':'Strategy Lab','comparison_assets':[sell,buy],'funded_switch':{'quantity':1,'fees_brl':0,'taxes_brl':0},'analysis_mode':'deterministic'}}
    funded_response=client.post('/orchestrate',json=funded_request)
    funded_data=funded_response.json()
    assert funded_response.status_code==200 and not funded_data.get('error')
    funded=funded_data['result']['funded_switch']
    assert abs(funded['purchase_notional_brl']+funded['residual_cash_brl']-funded['net_sale_proceeds_brl'])<1e-7
    assert funded_data['result']['telemetry']['llm_calls']==0
    write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/funded-switch',{'instance':'candidate ASGI with real portfolio and quotes, hypothetical explicit zero fees/taxes','response':funded_data})
    print('FUNDED_SWITCH_REAL=PASS cash_conservation=YES execution=NONE',flush=True)
    if args.senior:
        request=funded_request
        request['context'].pop('analysis_mode')
        request['task']='Compare manter as ações selecionadas versus vender para financiar a compra descrita. Explique evidências favoráveis e contrárias, fluxo de caixa, custo de oportunidade, restrições de opções relacionadas, incerteza de execução e dividendos/retorno futuro UNKNOWN. Os custos zero são hipóteses explícitas deste teste, não impostos reais. Não recomende trocar apenas por risco histórico.'
        started=monotonic()
        response=client.post('/orchestrate',json=request); data=response.json()
        result=data.get('result') or {}; proposal=result.get('proposal') or {}
        assessments=proposal.get('alternative_assessments') or []
        write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/stock-screen/senior',{'instance':'candidate ASGI with actual senior routing','request':request,'response':data})
        print(json.dumps({'case':'funded_switch_senior','http':response.status_code,'api_error':bool(data.get('error')),'elapsed_ms':round((monotonic()-started)*1000,1),'assessment_count':len(assessments),'source_count':len(data.get('sources') or []),'stages':result.get('telemetry',{}).get('stages',{})}),flush=True)
        assert response.status_code==200 and not data.get('error')
        assert {r['alternative_id'] for r in assessments}=={r['alternative_id'] for r in result['strategy_comparison']['alternatives']}
        assert len(assessments)==2
        assert 'funded_switch' in result
        assert all(r['decision_implications'] and r['unknowns'] for r in assessments)
    print('STOCK_SCREEN_REAL=PASS instance=candidate-ASGI not-systemd',flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
