"""Acquire reviewed primary report URLs and optionally project to existing Qdrant."""
import argparse
from dataclasses import asdict
import json
import os
from b3_agent.institution_target_ingestion import acquire_xp_report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url', action='append', required=True)
    parser.add_argument('--apply', action='store_true')
    args=parser.parse_args()
    if not 1 <= len(args.url) <= 20: parser.error('Provide 1 to 20 reviewed report URLs')
    evidence=[acquire_xp_report(url) for url in args.url]
    if args.apply:
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
    print(json.dumps({'case':'PRIMARY_TARGET_INGESTION','applied':args.apply,
        'reports':[{'ticker':item.metadata.ticker_refs[0], 'document_id':item.metadata.document_id,
                    'target':item.metadata.extra['price_target']} for item in evidence]}))

if __name__=='__main__': main()
