#!/usr/bin/env python3
"""Real Ubuntu conditional stock screen; metadata only in public Actions logs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from time import monotonic


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
    client=TestClient(app)
    assets=['VALE3','RENT3','VIVT3','BBAS3']
    for objective in ('LOWEST_REALIZED_VOLATILITY_60D','HIGHEST_OBSERVED_LIQUIDITY_20D'):
        started=monotonic()
        request={'task':'Compare the explicitly selected assets by the observed objective; never infer valuation or future return.', 'ticker':None,'context':{'workspace':'Opportunities','opportunity_assets':assets,'opportunity_objective':objective,'analysis_mode':'deterministic','research_mode':'stored_only'}}
        response=client.post('/orchestrate',json=request)
        data=response.json()
        assert response.status_code==200 and not data.get('error')
        result=data['result']; screen=result['opportunity_screen']
        assert result['telemetry']['llm_calls']==0
        assert set(result['asset_evidence'])==set(assets)
        assert len(screen['rows'])==4
        assert screen['ranked_count']>=2, 'Real provider data did not yield two comparable assets'
        assert all(row['expected_return'] is None for row in screen['rows'])
        print(json.dumps({'case':'stock_screen','objective':objective,'status':screen['status'],'elapsed_ms':round((monotonic()-started)*1000,1),'ranked_count':screen['ranked_count'],'rows':[{'ticker':r['ticker'],'history_count':r['history_count'],'rank_present':r['rank'] is not None,'exclusions':r['exclusions']} for r in screen['rows']],'llm_calls':0}),flush=True)
        write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/stock-screen'/objective,{'instance':'candidate ASGI with real production inputs','request':request,'response':data})
    from b3_agent.config import settings
    from b3_agent.portfolio.snapshot import load_active_snapshots
    portfolio=load_active_snapshots(settings.data_dir).get('portfolio_context')
    assert portfolio is not None, 'Real portfolio unavailable for funded switch acceptance'
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
