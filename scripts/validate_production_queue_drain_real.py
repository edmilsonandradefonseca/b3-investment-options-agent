"""Authorized production catch-up; report queue health without private content."""
import json
import os
from pathlib import Path
import subprocess
from time import monotonic


def main():
    pid=subprocess.check_output(['systemctl','show','b3-runtime.service','--property=MainPID','--value'],text=True).strip()
    for field in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0'):
        key,sep,value=field.partition(b'='); name=key.decode()
        if sep and (name.startswith('B3_') or name.startswith('LOCAL_REASONING_')):os.environ[name]=value.decode()
    os.environ['B3_AGENT_DATA_DIR']='/opt/b3-runtime/data'
    from b3_agent.config import settings
    from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
    from b3_agent.jobs.local_evidence_analyst import LocalEvidenceAnalystJob
    from validate_live_workspace_outputs import write_private_report
    queue=LocalEvidenceQueue(settings.data_dir/'derived'/'local_evidence_analyst')
    before=queue.outstanding_count()
    started=monotonic()
    print(json.dumps({'case':'PRODUCTION_CATCHUP_START','pending':before}),flush=True)
    result=LocalEvidenceAnalystJob(queue=queue).run_until_idle(limit=5,max_batches=20,max_seconds=1800)
    metrics={key:result[key] for key in ('batches','processed','ready','degraded','failed','deferred','remaining_queue','worker_busy')}
    metrics.update(case='PRODUCTION_CATCHUP_RESULT',pending_before=before,elapsed_ms=round((monotonic()-started)*1000,1))
    print(json.dumps(metrics),flush=True)
    write_private_report(Path.home()/'.local/share/b3-investment-options-agent/live-validation/production-catchup',result)
    assert not result['worker_busy'] and result['deferred']==result['failed']==result['degraded']==0, 'Production consumer requires follow-up'
    assert result['remaining_queue']==0, 'Catch-up budget exhausted; backlog not closed'
    print('PRODUCTION_QUEUE_DRAIN_REAL=PASS',flush=True)

if __name__=='__main__':main()
