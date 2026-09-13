from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class KnowledgeRecord:
    """Persistent semantic knowledge record."""

    knowledge_id: str
    topic: str
    category: str
    status: str
    version: str
    created_at: datetime
    updated_at: datetime
    source: str
    evidence: str
    content: str
    validated_at: datetime | None = None
    validated_by: str | None = None
    previous_version: str | None = None
