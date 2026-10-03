#!/usr/bin/env python3
"""Actual Ubuntu option-chain and senior acceptance; private response bodies."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime,timezone
from time import monotonic

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--senior',action='store_true');args=parser.parse_args()
    pid=subprocess.check_output(['systemctl','show','b3-runtime.service','--property=MainPID','--value'],text=True,timeout=10).strip()
    assert pid.isdecimal() and int(pid)>0
    for field in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0'):
        key,sep,value=field.partition(b'=');name=key.decode()
        if sep and (name.startswith('B3_') or name in {'OPLAB_API_TOKEN','BRAPI_TOKEN'}):os.environ[name]=value.decode()
    os.environ['B3_AGENT_DATA_DIR']='/opt/b3-runtime/data'
    os.environ['B3_AGENT_PROJECT_ROOT']=str(Path(__file__).resolve().parents[1])
    from fastapi.testclient import TestClient
    from b3_agent.server import app
    from b3_agent.providers.oplab.options import OplabOptionsAdapter
    from validate_live_workspace_outputs import write_private_report
    now=datetime.now(timezone.utc);contracts,quotes=OplabOptionsAdapter().get_snapshot('PETR4',now)
    quote_map={quote.option_id:quote for quote in quotes}
    eligible=[contract for contract in contracts if contract.option_type=='PUT' and contract.expiration_date>now.date() and contract.option_id in quote_map and (quote_map[contract.option_id].bid or 0)>0 and (quote_map[contract.option_id].ask or 0)>=(quote_map[contract.option_id].bid or 0)]
    eligible.sort(key=lambda contract:(contract.expiration_date,-(quote_map[contract.option_id].volume or 0),contract.option_id))
    assert eligible,'No two-sided positive-bid current PETR4 PUT available'
    first=eligible[0];second=next((contract for contract in eligible if contract.expiration_date!=first.expiration_date),None)
    assert second is not None,'No second expiry exists in actual chain'
    client=TestClient(app)
    for objective in ('HIGHEST_GROSS_PREMIUM_PER_CAPITAL_30D','LOWEST_MODEL_EXPIRY_ITM'):
        request={'task':'Compare these exact two PUT sales with different expiries; preserve UNKNOWN and separate ITM, touch and assignment.', 'context':{'workspace':'Strategy Lab','selected_ticker':None,'comparison_assets':['PETR4','PETR4'],'strategy_a':'Vender PUT','strategy_b':'Vender PUT','option_a':first.option_id,'option_b':second.option_id,'put_objective':objective,'analysis_mode':'deterministic','research_mode':'stored_only'}}
        started=monotonic();response=client.post('/orchestrate',json=request);data=response.json()
        assert response.status_code==200 and not data.get('error')
        result=data['result'];pair=result['put_pair_comparison']
        assert pair['different_expiries'] and len(pair['rows'])==2
        assert result['telemetry']['llm_calls']==0
        assert {row['option_id'] for row in pair['rows']}=={first.option_id,second.option_id}
        assert all(row['net_expected_return'] is None for row in pair['rows'])
        if objective=='HIGHEST_GROSS_PREMIUM_PER_CAPITAL_30D':assert pair['ranking'] in {'CONDITIONAL_OBJECTIVE_ONLY','TIE'}
        write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/put-pair'/objective,{'instance':'candidate ASGI actual chain','request':request,'response':data})
        print(json.dumps({'case':'different_expiry_put_pair','http':200,'objective':objective,'ranking':pair['ranking'],'elapsed_ms':round((monotonic()-started)*1000,1),'contracts':2,'llm_calls':0}),flush=True)
    if args.senior:
        request['context'].pop('analysis_mode');request['task']='Compare as duas PUTs selecionadas: prêmio por capital e prazo, break-even, perda máxima, liquidez, risco no próprio vencimento, estimativas ITM e toque não calibradas e exercício antecipado separado. Explique vantagens e desvantagens de cada contrato; não transforme prêmio bruto em retorno esperado nem probabilidade de modelo em frequência pessoal. Cite as fontes e preserve UNKNOWN nos custos e nas estimativas ausentes.'
        started=monotonic();response=client.post('/orchestrate',json=request);data=response.json()
        result=data.get('result') or {};assessments=(result.get('proposal') or {}).get('alternative_assessments') or []
        write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/put-pair/senior',{'instance':'candidate ASGI actual chain and senior','response':data})
        print(json.dumps({'case':'different_expiry_put_senior','http':response.status_code,'error':bool(data.get('error')),'assessments':len(assessments),'elapsed_ms':round((monotonic()-started)*1000,1)}),flush=True)
        assert response.status_code==200 and not data.get('error')
        assert {row['alternative_id'] for row in assessments}=={row['alternative_id'] for row in result['strategy_comparison']['alternatives']}
        assert len(assessments)==2 and all(row['decision_implications'] and row['unknowns'] for row in assessments)
    print('DIFFERENT_EXPIRY_PUT_REAL=PASS instance=candidate-ASGI',flush=True)

if __name__=='__main__':main()
