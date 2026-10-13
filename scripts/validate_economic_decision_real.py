#!/usr/bin/env python3
"""Actual quote economic what-if acceptance; no invented market forecast."""
import argparse,json,os,subprocess
from pathlib import Path
from time import monotonic
from datetime import datetime,timedelta,timezone

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
    context={'workspace':'Strategy Lab','comparison_assets':['ITUB4','BBDC4'],'strategy_a':'Comprar ação','strategy_b':'Comprar ação','comparison_amount':10000,'analysis_mode':'deterministic','research_mode':'stored_only'}
    response=client.post('/orchestrate',json={'task':'Get qualified current purchase evidence', 'context':context});data=response.json()
    assert response.status_code==200 and not data.get('error')
    rows=data['result']['stock_purchase_comparison']['rows'];prices={row['ticker']:row['current_price_brl'] for row in rows}
    assert all(price and price>0 for price in prices.values())
    scenario={'name':'Explicit asymmetric what-if','terminal_prices_brl':{'ITUB4':prices['ITUB4']*.95,'BBDC4':prices['BBDC4']*.90},'gross_dividends_per_share_brl':{'ITUB4':0,'BBDC4':0},'exit_costs_brl':{'ITUB4':0,'BBDC4':0}}
    context['economic_inputs']={'objective':'MAXIMIZE_WORST_CASE_NET_RETURN','horizon':(datetime.now(timezone.utc).date()+timedelta(days=90)).isoformat(),'entry_costs_brl':{'ITUB4':0,'BBDC4':0},'scenarios':[scenario]}
    request={'task':'Compare these explicitly hypothetical terminal prices, zero dividends and zero modeled costs. Do not label assumptions as forecasts or overall investment recommendation.', 'context':context}
    started=monotonic();response=client.post('/orchestrate',json=request);data=response.json()
    assert response.status_code==200 and not data.get('error')
    result=data['result'];economic=result['economic_decision']
    assert result['telemetry']['llm_calls']==0
    assert economic['ranking']=='CONDITIONAL_USER_SCENARIOS_ONLY'
    assert len(economic['rows'])==2 and all(row['quantity']>0 for row in economic['rows'])
    for row in economic['rows']:
        assert abs(row['purchase_notional_brl']+row['entry_costs_brl']+row['residual_cash_brl']-row['budget_brl'])<1e-7
        assert row['expected_return'] is None
        assert row['scenarios'][0]['net_scenario_pnl_brl'] is not None
    assert {row['alternative_id'] for row in economic['rows']}=={row['alternative_id'] for row in result['strategy_comparison']['alternatives']}
    write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/economic-decision/deterministic',{'request':request,'response':data})
    print(json.dumps({'case':'economic_decision','http':200,'elapsed_ms':round((monotonic()-started)*1000,1),'ranking':economic['ranking'],'llm_calls':0,'cash_conservation':'PASS','assumption_origin':economic['assumption_origin']}),flush=True)
    for row in result['stock_purchase_comparison']['rows']:
        evidence=row['economic_evidence']
        assert evidence['institution_target_potential'], 'No real primary institutional target reached the BUY comparison'
        assert evidence['quantity']>0
        assert evidence['expected_return'] is None
    opportunity_request={'task':'Compare sourced target potential for both stocks, preserve report opinions and unknown dividend forecasts.',
        'context':{'workspace':'Opportunities','opportunity_assets':['ITUB4','BBDC4'],'analysis_mode':'deterministic',
            'opportunity_economic_inputs':{'budget_brl':10000,'entry_costs_brl':{'ITUB4':0,'BBDC4':0},
                'target_institution':'XP','target_horizon':'2027-12-31'}}}
    started=monotonic();response=client.post('/orchestrate',json=opportunity_request);opportunity=response.json()
    assert response.status_code==200 and not opportunity.get('error')
    op=opportunity['result'];ranking=op['economic_target_ranking']
    assert ranking['status']=='CONDITIONAL_TARGET_POTENTIAL' and len(ranking['rows'])==2
    assert op['telemetry']['llm_calls']==0
    for row in op['opportunity_screen']['rows']:
        evidence=row['economic_evidence']
        assert evidence['quantity']>0 and evidence['institution_target_potential']
        assert abs(evidence['notional_brl']+evidence['entry_cost_brl']+evidence['residual_cash_brl']-10000)<1e-7
        assert evidence['expected_return'] is None
    write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/economic-decision/opportunities',{'request':opportunity_request,'response':opportunity})
    print(json.dumps({'case':'sourced_economic_opportunities','http':200,'elapsed_ms':round((monotonic()-started)*1000,1),
        'target_count':sum(len(r['economic_evidence']['institution_target_potential']) for r in op['opportunity_screen']['rows']),
        'ranking':ranking['status'],'cash_conservation':'PASS','llm_calls':0}),flush=True)
    if args.senior:
        request['context'].pop('analysis_mode');started=monotonic();response=client.post('/orchestrate',json=request);data=response.json()
        write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/economic-decision/senior',{'response':data})
        assert response.status_code==200 and not data.get('error')
        result=data['result'];assessments=(result.get('proposal') or {}).get('alternative_assessments') or []
        assert {row['alternative_id'] for row in assessments}=={row['alternative_id'] for row in result['strategy_comparison']['alternatives']}
        assert len(assessments)==2 and all(row['decision_implications'] and row['unknowns'] for row in assessments)
        print(json.dumps({'case':'economic_senior','http':200,'assessments':2,'elapsed_ms':round((monotonic()-started)*1000,1)}),flush=True)
        opportunity_request['context'].pop('analysis_mode')
        started=monotonic();response=client.post('/orchestrate',json=opportunity_request);data=response.json()
        write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/economic-decision/opportunities-senior',{'response':data})
        assert response.status_code==200 and not data.get('error')
        assessments=(data['result'].get('proposal') or {}).get('alternative_assessments') or []
        assert len(assessments)==2 and all(row['decision_implications'] for row in assessments)
        assert data['result']['economic_target_ranking']['status']=='CONDITIONAL_TARGET_POTENTIAL'
        print(json.dumps({'case':'sourced_opportunities_senior','http':200,'assessments':2,'elapsed_ms':round((monotonic()-started)*1000,1)}),flush=True)
    print('ECONOMIC_DECISION_REAL=PASS candidate-ASGI',flush=True)

if __name__=='__main__':main()
