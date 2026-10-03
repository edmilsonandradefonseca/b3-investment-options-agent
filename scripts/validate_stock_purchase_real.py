#!/usr/bin/env python3
"""Focused real Ubuntu BUY comparison, private payload and public metadata."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from time import monotonic


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--senior',action='store_true');args=parser.parse_args()
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
    request={'task':'Compare a compra de ITUB4 e BBDC4 por fundamentos, valorização e dividendos futuros. Use evidência qualificada, destaque lacunas e não invente estimativas.', 'context':{'workspace':'Strategy Lab','comparison_assets':['ITUB4','BBDC4'],'strategy_a':'Comprar ação','strategy_b':'Comprar ação','amount':10000,'analysis_mode':'deterministic','research_mode':'stored_only'}}
    started=monotonic();response=client.post('/orchestrate',json=request);data=response.json()
    assert response.status_code==200 and not data.get('error'), 'BUY pair HTTP failed'
    result=data['result'];pair=result['stock_purchase_comparison']
    assert len(pair['rows'])==2 and {row['ticker'] for row in pair['rows']}=={'ITUB4','BBDC4'}
    assert result['telemetry']['llm_calls']==0
    assert all(row['expected_return'] is None and row['future_dividend_per_share'] is None for row in pair['rows'])
    assert all(row['source_refs'] and row['evidence_refs'] for row in pair['rows'])
    write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/stock-purchase/deterministic',{'response':data})
    print(json.dumps({'case':'stock_purchase','http':200,'rows':2,'llm_calls':0,'elapsed_ms':round((monotonic()-started)*1000,1),'fundamental_counts':[len(row['fundamental_metrics']) for row in pair['rows']],'forward_forecast':'UNKNOWN'}),flush=True)
    if args.senior:
        request['context'].pop('analysis_mode');started=monotonic();response=client.post('/orchestrate',json=request);data=response.json()
        write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/stock-purchase/senior',{'response':data})
        assert response.status_code==200 and not data.get('error')
        result=data['result'];assessments=(result.get('proposal') or {}).get('alternative_assessments') or []
        assert {row['alternative_id'] for row in assessments}=={row['alternative_id'] for row in result['strategy_comparison']['alternatives']}
        assert len(assessments)==2 and all(row['decision_implications'] and row['unknowns'] for row in assessments)
        print(json.dumps({'case':'stock_purchase_senior','http':200,'assessments':2,'elapsed_ms':round((monotonic()-started)*1000,1)}),flush=True)
    print('STOCK_PURCHASE_REAL=PASS candidate-ASGI',flush=True)

if __name__=='__main__':main()
