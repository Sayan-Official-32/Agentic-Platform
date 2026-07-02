# routers/ingest_router.py
# This module implements the document ingestion endpoints (routes) for the API.
# It supports loading pre-packaged sample CSV data, uploading files (PDF/CSV) via HTTP multipart form-data,
# or triggering a batch directories scan to index documents into the Elasticsearch cluster.

import logging

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
import os
import tempfile
from pathlib import Path
from app.config.settings import settings
from app.data_ingest.file_ingest import (
    detect_file_type,
    load_documents_from_directory,
    load_documents_from_file,
    load_documents_from_csv
)
from app.dependencies.auth_dependencies import get_current_user
from app.models.auth_models import UserResponse
from app.models.ingest_models import (
    BatchIngestResponse,
    FileIngestResponse,
    IngestRequest,
    IngestResponse,
)
from app.services.search_service import SearchService

# APIRouter grouped under /api/v1/ingest tag
router = APIRouter(prefix=settings.api_prefix, tags=["ingest"])
logger = logging.getLogger(__name__)

# Initialize search service client
search_service = SearchService()


@router.post("/ingest/sample-data", response_model=IngestResponse)
def ingest_sample_data(current_user: UserResponse = Depends(get_current_user)) -> IngestResponse:
    """
    POST route that indexes default CSV sample business data (ai_tooling_catalog.csv).
    Requires a valid JWT bearer token.
    """
    logger.info("Sample ingest requested.", extra={"user_id": current_user.email})
    try:
        # 1. Load data records from standard CSV path
        documents = load_documents_from_csv("data/ai_tooling_catalog.csv")
        logger.info(
            "CSV documents loaded for ingest.",
            extra={"user_id": current_user.email, "document_count": len(documents)},
        )
        # 2. Push documents into Elasticsearch
        indexed_count = search_service.bulk_index_documents(documents)
        logger.info(
            "Sample ingest completed.",
            extra={"user_id": current_user.email, "indexed_count": indexed_count},
        )
        return IngestResponse(
            indexed_count=indexed_count,
            index_name=settings.elasticsearch_index,
            source_file="data/ai_tooling_catalog.csv",
        )
    except Exception as exc:
        logger.exception("Sample ingest failed.", extra={"user_id": current_user.email})
        # If any database or filesystem error occurs, return an HTTP 500 error code.
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/ingest/upload", response_model=FileIngestResponse)
async def ingest_uploaded_file(
    # file: UploadFile is the FastAPI declaration for receiving files via HTTP post multipart/form-data.
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user)
) -> FileIngestResponse:
    """
    POST route that processes a file uploaded directly by the user,
    extracts its text content, and indexes it into Elasticsearch.
    """
    logger.info(
        f"File upload ingest requested: {file.filename}",
        extra={"user_id": current_user.email}
    )
    
    # Verify that a filename was actually provided
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check if the file suffix is supported (.pdf or .csv)
    try:
        file_type = detect_file_type(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    
    temp_file = None
    temp_file_path = ""
    try:
        # Since loaders require file paths to read, we must write the uploaded in-memory bytes
        # to a temporary file on the server disk first.
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read() # Read incoming bytes stream
            temp_file.write(content)     # Write bytes to temp file
            temp_file_path = temp_file.name
        
        logger.info(
            f"File saved to temporary location: {temp_file_path}",
            extra={"user_id": current_user.email}
        )
        
        # Parse the documents from the temporary path
        documents = load_documents_from_file(temp_file_path, file_type)
        
        logger.info(
            f"Loaded {len(documents)} documents from {file.filename}",
            extra={"user_id": current_user.email, "document_count": len(documents)}
        )
        
        # Index document snippets into Elasticsearch
        indexed_count = search_service.bulk_index_documents(documents)
        
        logger.info(
            f"File ingest completed: {file.filename}",
            extra={"user_id": current_user.email, "indexed_count": indexed_count}
        )
        
        return FileIngestResponse(
            indexed_count=indexed_count,
            index_name=settings.elasticsearch_index,
            file_name=file.filename,
            file_type=file_type,
            documents_processed=len(documents)
        )
        
    except Exception as exc:
        logger.exception(
            f"File ingest failed: {file.filename}",
            extra={"user_id": current_user.email}
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    
    finally:
        # IMPORTANT: The 'finally' block always runs, ensuring temporary files
        # are deleted to prevent disk usage leaks.
        if temp_file and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path) # Delete temporary file from disk
                logger.debug(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {e}")
 
 
@router.post("/ingest/batch", response_model=BatchIngestResponse)
def ingest_batch_from_directory(
    current_user: UserResponse = Depends(get_current_user),
    # Body specifies that request variables are parsed from the raw JSON post body
    request: IngestRequest = Body(default=IngestRequest())
) -> BatchIngestResponse:
    """
    POST route that triggers a bulk scan of files from a folder on the server.
    Useful for backend importing or indexing local file storage.
    """
    logger.info(
        f"Batch ingest requested from directory: {request.directory_path}",
        extra={"user_id": current_user.email}
    )
    
    try:
        file_types_list = request.file_types if request.file_types else None
        # 1. Scan and parse all documents in target folder
        results = load_documents_from_directory(
            request.directory_path,
            file_types=file_types_list,  # type: ignore
            recursive=request.recursive
        )
        
        # If the directory was empty, return success with 0 indexed documents
        if not results:
            logger.warning(
                f"No files found in directory: {request.directory_path}",
                extra={"user_id": current_user.email}
            )
            return BatchIngestResponse(
                total_files_processed=0,
                total_documents_indexed=0,
                index_name=settings.elasticsearch_index,
                files_summary=[],
                errors=["No files found in the specified directory"]
            )
        
        files_summary = []
        errors = []
        total_indexed = 0
        
        # 2. Iterate through matched files and bulk index their snippets
        for file_path, documents in results.items():
            try:
                indexed_count = search_service.bulk_index_documents(documents)
                total_indexed += indexed_count
                
                files_summary.append({
                    "file_path": file_path,
                    "documents_processed": len(documents),
                    "documents_indexed": indexed_count,
                    "status": "success"
                })
                
                logger.info(
                    f"Indexed {indexed_count} documents from {file_path}",
                    extra={"user_id": current_user.email}
                )
                
            except Exception as e:
                # If one file fails, we capture the error but continue indexing other files.
                error_msg = f"Failed to index {file_path}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, extra={"user_id": current_user.email})
                
                files_summary.append({
                    "file_path": file_path,
                    "documents_processed": len(documents),
                    "documents_indexed": 0,
                    "status": "failed",
                    "error": str(e)
                })
        
        logger.info(
            f"Batch ingest completed: {len(results)} files, {total_indexed} documents",
            extra={"user_id": current_user.email}
        )
        
        return BatchIngestResponse(
            total_files_processed=len(results),
            total_documents_indexed=total_indexed,
            index_name=settings.elasticsearch_index,
            files_summary=files_summary,
            errors=errors if errors else None
        )
        
    except FileNotFoundError as exc:
        logger.error(
            f"Directory not found: {request.directory_path}",
            extra={"user_id": current_user.email}
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    
    except Exception as exc:
        logger.exception(
            f"Batch ingest failed from directory: {request.directory_path}",
            extra={"user_id": current_user.email}
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

