"""Replay real stored non-target bundles privately; publish operational metrics only."""
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from time import monotonic


def main():
    pid=subprocess.check_output(['systemctl','show','b3-runtime.service','--property=MainPID','--value'],text=True).strip()
    for field in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0'):
        key,sep,value=field.partition(b'='); name=key.decode()
        if sep and (name.startswith('B3_') or name.startswith('LOCAL_REASONING_')):os.environ[name]=value.decode()
    os.environ['B3_AGENT_DATA_DIR']='/opt/b3-runtime/data'
    from b3_agent.config import settings
    from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue, LocalEvidenceAnalyst
    from b3_agent.jobs.local_evidence_analyst import LocalEvidenceAnalystJob
    from validate_live_workspace_outputs import write_private_report
    production=LocalEvidenceQueue(settings.data_dir/'derived'/'local_evidence_analyst')
    requests=production.pending()
    selected=[]; kinds=set()
    for request in requests:
        types={e.get('evidence_type') for e in request.evidence_events}
        if types == {'institution_price_target'}:continue
        group='dividends' if 'issuer_dividends' in types else 'news_or_disclosure'
        if group in kinds:continue
        selected.append((group,request));kinds.add(group)
        if len(selected)==2:break
    if 'news_or_disclosure' not in kinds:
        from datetime import datetime, timezone, timedelta
        from types import SimpleNamespace
        from b3_agent.intelligence.stored_research import StoredResearchContextService
        for ticker in ['PETR4','VALE3','ITUB4','BBDC4','BBAS3']:
            stored=StoredResearchContextService().build(ticker,as_of=datetime.now(timezone.utc),limit=3,max_age=timedelta(days=180))
            if not stored['events']:continue
            events=[{'evidence_type':'open_web_event','evidence_id':e['event_id'],'source_ref':e['source_ref'],
                'published_at':e['published_at'].isoformat(),'headline':e['headline'],'summary':e['summary']} for e in stored['events']]
            selected.append(('news_or_disclosure',SimpleNamespace(ticker=ticker,evidence_events=events)))
            kinds.add('news_or_disclosure')
            break
    assert selected, 'No real non-target bundle available for broad validation'
    timer=subprocess.check_output(['systemctl','cat','b3-local-evidence-analyst.timer'],text=True)
    print(json.dumps({'case':'INSTALLED_CONSUMER_SCHEDULE','calendar':[line.split('=',1)[1] for line in timer.splitlines() if line.startswith('OnCalendar=')],
        'production_pending_before':production.outstanding_count(),'replay_classes':sorted(kinds)}),flush=True)
    reports=[]
    with TemporaryDirectory(prefix='b3-broad-worker-') as directory:
        queue=LocalEvidenceQueue(directory)
        for group,request in selected:
            enqueued=queue.enqueue(request.ticker,request.evidence_events)
            started=monotonic()
            result=LocalEvidenceAnalystJob(queue=queue).run_until_idle(limit=1,max_batches=1,max_seconds=600)
            dossier=queue.latest(request.ticker)
            metrics={'case':'REAL_BROAD_LOCAL_WORKER','bundle_class':group,'event_count':len(request.evidence_events),
                'status':dossier.status.value if dossier else 'ABSENT','quality_flags':list(dossier.quality_flags) if dossier else [],
                'model':dossier.model if dossier else None,'input_chars':dossier.input_chars if dossier else None,
                'eval_count':dossier.eval_count if dossier else None,'elapsed_ms':round((monotonic()-started)*1000,1),
                'summary_chars':len((dossier.analysis or {}).get('summary','')) if dossier else None}
            print(json.dumps(metrics),flush=True)
            reports.append({'metrics':metrics,'source_request':{'ticker':request.ticker,'events':request.evidence_events},'dossier':dossier.as_dict() if dossier else None,'manifest':result})
        write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/broad-async-worker',{'cases':reports})
    assert kinds=={'dividends','news_or_disclosure'}, 'News or disclosure corpus unavailable; broad acceptance remains incomplete'
    assert all(row['metrics']['status']=='READY' and not row['metrics']['quality_flags'] for row in reports), 'Broad bundle admission failed'
    print(json.dumps({'case':'PRODUCTION_QUEUE_OBSERVATION','remaining':production.outstanding_count(),'replay_writes_to_production':False}),flush=True)
    print('BROAD_ASYNC_WORKER_REAL=PASS isolated-real-bundles; semantic expert review remains separate',flush=True)

if __name__=='__main__':main()
