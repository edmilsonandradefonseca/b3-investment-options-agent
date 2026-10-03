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
    if args.senior:
        request['context'].pop('analysis_mode')
        request['task']='Compare VALE3, RENT3, VIVT3 e BBAS3 pelo objetivo explícito observado. Explique evidências favoráveis e contrárias por ativo, impacto e custo de oportunidade quando conhecidos; preserve UNKNOWN em valuation e retorno futuro. Não recomende compra apenas por menor risco/maior liquidez históricos.'
        started=monotonic()
        response=client.post('/orchestrate',json=request); data=response.json()
        result=data.get('result') or {}; proposal=result.get('proposal') or {}
        assessments=proposal.get('alternative_assessments') or []
        write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/stock-screen/senior',{'instance':'candidate ASGI with actual senior routing','request':request,'response':data})
        print(json.dumps({'case':'stock_screen_senior','http':response.status_code,'api_error':bool(data.get('error')),'elapsed_ms':round((monotonic()-started)*1000,1),'assessment_count':len(assessments),'source_count':len(data.get('sources') or []),'stages':result.get('telemetry',{}).get('stages',{})}),flush=True)
        assert response.status_code==200 and not data.get('error')
        assert {r['alternative_id'] for r in assessments}==set(assets)
        assert all(r['decision_implications'] and r['unknowns'] for r in assessments)
    print('STOCK_SCREEN_REAL=PASS instance=candidate-ASGI not-systemd',flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
