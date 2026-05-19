from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Node(BaseModel):
    id: str
    type: str  # Scheme, Ministry, District, Outcome, Beneficiary, etc.
    properties: Dict[str, Any] = Field(default_factory=dict)
    source_chunk_id: Optional[str] = None
    confidence: float = 1.0
    created_at: datetime = Field(default_factory=datetime.now)

class Edge(BaseModel):
    id: Optional[str] = None
    subject_id: str
    predicate: str
    object_id: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    source_chunk_id: Optional[str] = None
    confidence: float = 1.0
    created_at: datetime = Field(default_factory=datetime.now)

class ExtractionResult(BaseModel):
    nodes: List[Node]
    edges: List[Edge]
