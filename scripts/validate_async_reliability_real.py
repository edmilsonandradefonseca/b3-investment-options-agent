"""Real source discovery and Qwen multi-batch consumption, isolated from production queue."""
import json
import os
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic, sleep


def main():
    pid = subprocess.check_output(['systemctl', 'show', 'b3-runtime.service', '--property=MainPID', '--value'], text=True).strip()
    for field in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0'):
        key, sep, value = field.partition(b'=')
        name = key.decode()
        if sep and (name.startswith('B3_') or name.startswith('LOCAL_REASONING_')):
            os.environ[name] = value.decode()
    os.environ['B3_AGENT_DATA_DIR'] = '/opt/b3-runtime/data'
    from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
    from b3_agent.jobs.local_evidence_analyst import LocalEvidenceAnalystJob
    from b3_agent.jobs.primary_targets import enqueue_target
    from b3_agent.jobs.institution_target_discovery import InstitutionTargetDiscoveryJob
    from b3_agent.jobs.continuous_intelligence import _monitored_tickers
    from b3_agent.institution_target_ingestion import reviewed_evidence
    from validate_live_workspace_outputs import write_private_report
    print(json.dumps({'case': 'MONITORED_UNIVERSE', 'asset_count': len(_monitored_tickers())}), flush=True)
    with TemporaryDirectory(prefix='b3-async-reliability-') as directory:
        queue = LocalEvidenceQueue(Path(directory) / 'discovery')
        discovery = InstitutionTargetDiscoveryJob(queue=queue, project=lambda items: None).run(['ITUB4', 'BBDC4'])
        print(json.dumps({'case': 'REAL_INSTITUTION_DISCOVERY', 'statuses': dict(Counter(row['status'] for row in discovery['results'])),
                          'projected_facts_persisted': False, 'llm_calls': 0}), flush=True)
        queue = LocalEvidenceQueue(Path(directory) / 'consumer')
        manifest = json.loads((Path(__file__).resolve().parents[1] / 'docs/research/institution_targets_reviewed.json').read_text())
        for raw in manifest['evidence']:
            enqueue_target(queue, reviewed_evidence(raw, datetime.now(timezone.utc)))
        started = monotonic()
        job = LocalEvidenceAnalystJob(queue=queue)
        deadline = started + 360
        rows = []
        batches = 0
        worker_busy = False
        while queue.outstanding_count() and monotonic() < deadline:
            # Respect the queue's persisted backoff and the shared inference lock.
            # An idle batch with delayed requests does not mean the queue drained.
            if not queue.pending(limit=1):
                sleep(min(5, max(0, deadline - monotonic())))
                continue
            batch = job.run_until_idle(limit=1, max_batches=20, max_seconds=max(0.01, deadline - monotonic()))
            rows.extend(batch['results'])
            batches += batch['batches']
            worker_busy = worker_busy or batch['worker_busy']
            if batch['failed'] or batch['degraded']:
                break
            if batch['worker_busy']:
                sleep(min(5, max(0, deadline - monotonic())))
        result = {'batches': batches, 'worker_busy': worker_busy,
                  'processed': len(rows), 'remaining_queue': queue.outstanding_count(), 'results': rows}
        for key, status in (('ready', 'READY'), ('degraded', 'DEGRADED'), ('failed', 'FAILED'), ('deferred', 'DEFERRED')):
            result[key] = sum(row['status'] == status for row in rows)
        write_private_report(Path.home() / '.local/share/b3-investment-options-agent/live-validation/async-reliability',
                             {'manifest': result, 'dossiers': [json.loads(path.read_text()) for path in queue.runs_dir.glob('*.json')]})
        print(json.dumps({'case': 'REAL_MULTI_BATCH_QWEN', **{key: result[key] for key in ('batches', 'processed', 'ready', 'degraded', 'failed', 'deferred', 'remaining_queue')},
                          'worker_busy': result.get('worker_busy', False),
                          'quality_flag_counts': dict(Counter(flag for row in result['results'] for flag in row.get('quality_flags', []))),
                          'elapsed_ms': round((monotonic() - started) * 1000, 1)}), flush=True)
        assert result['ready'] == len(manifest['evidence']), 'Not all evidence became READY within the bounded retry window'
        assert len({row['analysis_id'] for row in rows if row['status'] == 'READY'}) == len(manifest['evidence'])
        assert result['remaining_queue'] == result['degraded'] == result['failed'] == 0
    print('ASYNC_RELIABILITY_REAL=PASS isolated-queue; source coverage states remain explicit', flush=True)


if __name__ == '__main__':
    main()
