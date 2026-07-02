# models/file_models.py
# This module defines Pydantic data models for file management, file listing responses,
# and similarity search chunks returned from the database.

from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class UserFileResponse(BaseModel):
    """Represents a metadata record for an uploaded user file."""
    id: UUID
    file_name: str
    file_type: str         # pdf | docx | txt | csv | xlsx | pptx | html | json | md
    status: str            # processing | ready | failed
    chunk_count: int
    file_size: Optional[int] = None
    created_at: datetime

class FileIngestResponse(BaseModel):
    """Standard payload returned after file upload ingestion succeeds."""
    file_id: UUID
    file_name: str
    file_type: str
    chunks_created: int
    storage_path: str
    status: str

class ChunkResult(BaseModel):
    """Represents a matching document chunk fragment from pgvector similarity searches."""
    chunk_id: UUID
    file_id: UUID
    file_name: str
    content: str
    score: float           # Cosine similarity score
    rerank_score: Optional[float] = None
    page_number: Optional[int] = None
    section: Optional[str] = None
    chunk_index: int
