"""Background refresh of reviewed report URLs; no inline model calls.

Discovery of other institutions/new report URLs remains a separate collector
capability. HTTP403 fallback retains the original acquisition/publication dates.
"""
from datetime import datetime,timezone
import json
from pathlib import Path
from urllib.error import HTTPError
from b3_agent.institution_target_ingestion import acquire_institution_report,reviewed_evidence
from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
from b3_agent.config import settings


def project_targets(evidence):
    import os
    from qdrant_client import QdrantClient
    from b3_agent.knowledge.qdrant_store import QdrantVectorStore
    from b3_agent.knowledge.embeddings import HttpEmbeddingProvider
    from b3_agent.knowledge.chunking import EvidenceChunker
    from b3_agent.knowledge.ingestion import VectorIngestionPipeline
    client=QdrantClient(url=os.getenv('B3_QDRANT_URL','http://127.0.0.1:6333'),timeout=10)
    try:
        pipeline=VectorIngestionPipeline(chunker=EvidenceChunker(),
            embeddings=HttpEmbeddingProvider(base_url=os.getenv('B3_EMBEDDING_URL','http://127.0.0.1:8093'),dimensions=768,timeout=15),
            store=QdrantVectorStore(client=client,collection_name='b3_evidence_768_hybrid',vector_size=768,hybrid=True))
        for item in evidence: pipeline.ingest(item)
    finally: client.close()


def enqueue_target(queue,item):
    m=item.metadata
    # Versioned report identity and factual summary stay stable across refreshes.
    event={'evidence_type':'institution_price_target','evidence_id':item.evidence_id,
        'ticker_refs':list(m.ticker_refs),'published_at':m.published_at.isoformat(),
        'headline':item.title,'summary':item.content,'source_name':m.extra['price_target']['institution'],
        'source_ref':m.source,'price_target':m.extra['price_target']}
    return queue.enqueue(m.ticker_refs[0],[event]).queue_status


class PrimaryTargetRefreshJob:
    def __init__(self,*,acquire=acquire_institution_report,project=project_targets,queue=None):
        self.acquire=acquire;self.project=project
        self.queue=queue or LocalEvidenceQueue(settings.data_dir/'derived'/'local_evidence_analyst')

    def run(self,manifest_path,*,tickers=None):
        manifest=json.loads(Path(manifest_path).read_text())
        if manifest.get('schema_version')!='reviewed-primary-target-evidence-v1': raise ValueError('Unsupported reviewed source manifest')
        records=manifest['evidence']
        if len(records)>20: raise ValueError('At most twenty reviewed sources per background refresh')
        results=[]
        for raw in records:
            ticker=raw['metadata']['extra']['price_target']['ticker']
            if tickers is not None and ticker not in tickers: continue
            try:
                try:
                    evidence=self.acquire(raw['source_url']); acquisition='LIVE_PRIMARY_READ'
                except HTTPError as exc:
                    if exc.code!=403: raise
                    evidence=reviewed_evidence(raw,datetime.now(timezone.utc))
                    acquisition='HTTP403_IMPORTED_REVIEWED_PRIMARY_RECORD'
                self.project([evidence])
                queued=enqueue_target(self.queue,evidence)
                results.append({'ticker':ticker,'status':'PROJECTED','acquisition_status':acquisition,'queue_status':queued,'document_id':evidence.metadata.document_id})
            except Exception as exc:
                results.append({'ticker':ticker,'status':'UNAVAILABLE','error_type':type(exc).__name__})
        return {'policy_version':'primary-target-background-v1','llm_calls':0,'results':results,
            'limitations':['Refresh covers reviewed URLs only; new report discovery uses a separate bounded job with XP, Safra and Itau parsers.',
                'The configured local model consumes the existing queue separately and does not authorize numeric financial facts.']}
