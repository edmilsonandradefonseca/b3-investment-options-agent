"""Knowledge, evidence, retrieval and graph primitives."""

from .chunking import EvidenceChunk, EvidenceChunker
from .embeddings import DeterministicEmbeddingProvider, Embedding, EmbeddingProvider
from .evidence import Evidence, EvidenceKind, EvidenceMetadata
from .ingestion import VectorIngestionPipeline, VectorIngestionResult
from .qdrant_store import QdrantVectorStore
from .retrieval_pipeline import PointInTimeVectorRetriever
from .semantic_retrieval import FreshnessScorer, RetrievalStrategy, VectorRetriever
from .vector_store import MetadataFilter, VectorSearchResult, VectorStore

__all__ = [
    "Evidence",
    "EvidenceKind",
    "EvidenceMetadata",
    "EvidenceChunk",
    "EvidenceChunker",
    "Embedding",
    "EmbeddingProvider",
    "DeterministicEmbeddingProvider",
    "MetadataFilter",
    "VectorSearchResult",
    "VectorStore",
    "QdrantVectorStore",
    "VectorIngestionPipeline",
    "VectorIngestionResult",
    "RetrievalStrategy",
    "VectorRetriever",
    "PointInTimeVectorRetriever",
    "FreshnessScorer",
]

from .learning_semantic import (
    B3_SEMANTIC_COLLECTION,
    B3_SEMANTIC_DIMENSIONS,
    B3_SEMANTIC_MODEL,
    LearningSemanticIndex,
)
