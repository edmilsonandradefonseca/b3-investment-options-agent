"""Acquire reviewed primary report URLs and optionally project to existing Qdrant."""
import argparse
from dataclasses import asdict
import json
import os
from datetime import datetime,timezone
from pathlib import Path
from urllib.error import HTTPError
from b3_agent.institution_target_ingestion import acquire_institution_report, reviewed_evidence


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url', action='append', required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--reviewed-fallback')
    args=parser.parse_args()
    if not 1 <= len(args.url) <= 20: parser.error('Provide 1 to 20 reviewed report URLs')
    evidence=[]; statuses=[]
    fallback=None
    if args.reviewed_fallback:
        fallback=json.loads(Path(args.reviewed_fallback).read_text())
        if fallback.get('schema_version')!='reviewed-primary-target-evidence-v1': raise ValueError('Unsupported reviewed manifest')
    for url in args.url:
        try:
            evidence.append(acquire_institution_report(url));statuses.append('LIVE_PRIMARY_READ')
        except HTTPError as exc:
            if exc.code!=403 or fallback is None: raise
            matches=[r for r in fallback['evidence'] if r['source_url']==url]
            if len(matches)!=1: raise ValueError('No unique reviewed source for blocked report')
            evidence.append(reviewed_evidence(matches[0],datetime.now(timezone.utc)))
            statuses.append('HTTP403_IMPORTED_REVIEWED_PRIMARY_RECORD')
    if args.apply:
        from b3_agent.jobs.primary_targets import project_targets,enqueue_target
        from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
        from b3_agent.config import settings
        project_targets(evidence)
        queue=LocalEvidenceQueue(settings.data_dir/'derived'/'local_evidence_analyst')
        queues=[enqueue_target(queue,item) for item in evidence]
    else:
        queues=[]
    print(json.dumps({'case':'PRIMARY_TARGET_INGESTION','applied':args.apply,'acquisition_statuses':statuses,'local_queue_statuses':queues,
        'reports':[{'ticker':item.metadata.ticker_refs[0], 'document_id':item.metadata.document_id,
                    'target':item.metadata.extra['price_target']} for item in evidence]}))

if __name__=='__main__': main()
