"""Actual background dividend projection and one existing local worker request."""
import json,os,subprocess
from pathlib import Path
from datetime import datetime,timezone
from time import monotonic


def main():
    pid=subprocess.check_output(['systemctl','show','b3-runtime.service','--property=MainPID','--value'],text=True,timeout=10).strip()
    assert pid.isdecimal() and int(pid)>0
    for field in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0'):
        key,sep,value=field.partition(b'=');name=key.decode()
        if sep and (name.startswith('B3_') or name.startswith('LOCAL_REASONING_') or name in {'BRAPI_TOKEN','OPLAB_API_TOKEN'}): os.environ[name]=value.decode()
    os.environ['B3_AGENT_DATA_DIR']='/opt/b3-runtime/data'
    os.environ['B3_AGENT_PROJECT_ROOT']=str(Path(__file__).resolve().parents[1])
    from b3_agent.jobs.dividend_refresh import DividendRefreshJob
    from b3_agent.stored_dividends import StoredDividendService
    from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue,build_request
    from b3_agent.jobs.local_evidence_analyst import LocalEvidenceAnalystJob
    from b3_agent.config import settings
    from validate_live_workspace_outputs import write_private_report
    started=monotonic();manifest=DividendRefreshJob().run(['ITUB4','BBDC4'])
    assert all(row['status']=='PROJECTED' for row in manifest['results'])
    service=StoredDividendService();reads=[service.build(t,datetime.now(timezone.utc)) for t in ['ITUB4','BBDC4']]
    assert all(row.get('read_origin')=='STORED_ASYNC_SNAPSHOT' for row in reads)
    assert any(row['records'] for row in reads)
    print(json.dumps({'case':'ASYNC_DIVIDENDS','elapsed_ms':round((monotonic()-started)*1000,1),'collection_statuses':[r['status'] for r in reads],'event_counts':[len(r['records']) for r in reads],'llm_calls':0}),flush=True)
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from b3_agent.server import app
    from b3_agent.providers.brapi.fundamentals import BrapiFundamentalsAdapter
    client=TestClient(app)
    requests=[{'task':'Stored dividend purchase comparison','context':{'workspace':'Strategy Lab','comparison_assets':['ITUB4','BBDC4'],'strategy_a':'Comprar ação','strategy_b':'Comprar ação','comparison_amount':10000,'analysis_mode':'deterministic','research_mode':'stored_only'}},
        {'task':'Stored dividend stock screen','context':{'workspace':'Opportunities','opportunity_assets':['ITUB4','BBDC4'],'analysis_mode':'deterministic'}}]
    with patch.object(BrapiFundamentalsAdapter,'get_dividends',side_effect=AssertionError('Interactive path attempted provider dividend collection')) as blocked:
        for request in requests:
            started=monotonic();response=client.post('/orchestrate',json=request);data=response.json()
            assert response.status_code==200 and not data.get('error')
            rows=(data['result'].get('stock_purchase_comparison') or data['result']['opportunity_screen'])['rows']
            assert all(r['dividends']['read_origin']=='STORED_ASYNC_SNAPSHOT' for r in rows)
            print(json.dumps({'case':'READ_ONLY_DIVIDEND_PATH','workspace':request['context']['workspace'],'http':200,'elapsed_ms':round((monotonic()-started)*1000,1),'provider_dividend_calls':blocked.call_count}),flush=True)
        assert blocked.call_count==0
    queue=LocalEvidenceQueue(settings.data_dir/'derived'/'local_evidence_analyst')
    from b3_agent.intelligence.local_evidence_analysis import PROMPT_VERSION
    pending=[r for r in queue.pending() if r.prompt_version == PROMPT_VERSION and any(e.get('evidence_type')=='institution_price_target' for e in r.evidence_events)]
    if pending:
        selected=pending[0]
        class FocusedQueue:
            def pending(self,limit=None): return [selected]
            def __getattr__(self,key): return getattr(queue,key)
        started=monotonic();result=LocalEvidenceAnalystJob(queue=FocusedQueue()).run(limit=1)
        write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/async-economic/local-worker',result)
        print(json.dumps({'case':'LOCAL_ADMISSION','ready':result['ready'],'degraded':result['degraded'],'failed':result['failed'],'deferred':result['deferred'],'quality_flags':[row['quality_flags'] for row in result['results']]}),flush=True)
        assert result['ready']==1 and result['failed']==result['degraded']==result['deferred']==0, 'Real local target dossier did not pass admission'
        print(json.dumps({'case':'REAL_LOCAL_TARGET_WORKER','status':'READY','model':LocalEvidenceAnalystJob().analyst.client.model,'processed':1,'elapsed_ms':round((monotonic()-started)*1000,1)}),flush=True)
    else:
        candidates=[]
        for path in queue.runs_dir.glob('*.json'):
            data=json.loads(path.read_text())
            if data.get('status')=='READY' and data.get('prompt_version') == PROMPT_VERSION and data.get('model') == LocalEvidenceAnalystJob().analyst.client.model and any('conteudos.xpi.com.br/acoes/relatorios/' in str(r) for r in data.get('evidence_refs',[])):
                candidates.append(data)
        assert candidates,'No queued target request or admitted target dossier'
        print(json.dumps({'case':'REAL_LOCAL_TARGET_WORKER','status':'PREVIOUSLY_READY','count':len(candidates)}),flush=True)
    for name in ['b3-nightly-intelligence.timer','b3-local-evidence-analyst.timer']:
        state=subprocess.run(['systemctl','is-active',name],text=True,capture_output=True,timeout=10).stdout.strip()
        print(json.dumps({'case':'ASYNC_TIMER_STATE','unit':name,'state':state}),flush=True)
    print('ASYNC_ECONOMIC_REAL=PASS candidate-producer existing-worker',flush=True)

if __name__=='__main__':main()
