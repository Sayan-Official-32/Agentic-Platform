# models/ingest_models.py
# This module defines Pydantic data schemas representing the inputs and outputs of document ingestion operations.
# These models map directory routes and document scanning queries to structured responses indicating index progress.

from typing import List, Optional

from pydantic import BaseModel, Field

class IngestResponse(BaseModel):
    """
    Response returned when successfully indexing snippets from a raw source file.
    """
    indexed_count: int      # Number of chunks successfully pushed into Supabase
    index_name: str         # The name of the Supabase Storage bucket where they were saved
    source_file: str        # Filename/path that was processed

class FileIngestResponse(BaseModel):
    """
    Detailed response returned after processing a single file upload/ingest.
    """
    indexed_count: int      # Number of search documents indexed
    index_name: str         # Supabase target bucket name
    file_name: str          # Name of the processed file
    file_type: str          # Detected extension type ('pdf' or 'csv')
    documents_processed: int # Total raw paragraphs or rows extracted

class BatchIngestResponse(BaseModel):
    """
    Response returned after bulk processing multiple files in a directory.
    """
    total_files_processed: int        # Count of files processed (e.g. 5 PDFs and 3 CSVs)
    total_documents_indexed: int      # Cumulative sum of document snippets stored in Elasticsearch
    index_name: str                   # Destination index name
    files_summary: List[dict] = Field(default_factory=list) # Detailed breakdown per processed file
    errors: Optional[List[str]] = Field(default_factory=list) # Messages for any files that failed to process
    
class IngestRequest(BaseModel):
    """
    Payload schema to trigger directory scanning and document ingestion.
    """
    directory_path: str = Field(default="data", description="Directory path to ingest files from")
    file_types: Optional[List[str]] = Field(default=None, description="File types to process (pdf, csv)")
    recursive: bool = Field(default=False, description="Whether to search subdirectories recursively")
