# routers/ingest_router.py
# This module implements the file ingestion API routes.
# It processes files (PDF, DOCX, TXT, CSV, XLSX, PPTX, HTML, JSON, MD),
# uploads them to Supabase Storage, chunks them, computes embeddings, and stores them in pgvector.

import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.config.settings import settings
from app.data_ingest.file_ingest import detect_file_type, load_documents_from_file
from app.data_ingest.chunker import chunk_text
from app.dependencies.auth_dependencies import get_current_user
from app.models.auth_models import UserResponse
from app.models.file_models import FileIngestResponse
from app.services.supabase_service import SupabaseService
from app.services.storage_service import StorageService
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService

router = APIRouter(prefix=settings.api_prefix + "/ingest", tags=["ingest"])
logger = logging.getLogger(__name__)

supabase = SupabaseService.get_client()
storage_service = StorageService()
embedding_service = EmbeddingService()
vector_service = VectorService()


@router.post("/upload", response_model=FileIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_uploaded_file(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user)
) -> FileIngestResponse:
    """
    Ingests an uploaded file: saves metadata, uploads to Storage, chunks text,
    embeds, and stores in pgvector.
    """
    logger.info(f"Ingesting file: {file.filename}", extra={"user_id": str(current_user.id)})
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
        
    try:
        file_type = detect_file_type(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Read bytes for Storage upload
    content_bytes = await file.read()
    file_size = len(content_bytes)

    # 1. Create file record in processing state
    file_id = uuid.uuid4()
    storage_path = f"{current_user.id}/{file_id}/{file.filename}"
    
    try:
        supabase.table("user_files").insert({
            "id": str(file_id),
            "user_id": str(current_user.id),
            "file_name": file.filename,
            "file_type": file_type,
            "storage_path": storage_path,
            "file_size": file_size,
            "status": "processing"
        }).execute()
    except Exception as exc:
        logger.error(f"Failed to create file record in DB: {exc}")
        raise HTTPException(status_code=500, detail="Database write failure.")

    # 2. Upload file to Supabase Storage
    try:
        storage_service.upload_file(str(current_user.id), str(file_id), file.filename, content_bytes)
    except Exception as exc:
        supabase.table("user_files").update({
            "status": "failed",
            "error_message": f"Storage upload failed: {exc}"
        }).eq("id", str(file_id)).execute()
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {exc}")

    # 3. Parse and chunk file text content
    temp_file_path = ""
    try:
        # Write to temp file for local parsing libraries
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content_bytes)
            temp_file_path = temp_file.name

        documents = load_documents_from_file(temp_file_path, file_type)
        
        chunks = []
        metadata_list = []
        for doc in documents:
            sub_chunks = chunk_text(doc["content"])
            for sub_chunk in sub_chunks:
                chunks.append(sub_chunk)
                # Keep parent document metadata (like page_number)
                metadata_list.append(doc["metadata"].copy())

        # 4. Generate batch embeddings
        embeddings = embedding_service.embed_batch(chunks)

        # 5. Store chunks in database
        vector_service.store_chunks(
            user_id=current_user.id,
            file_id=file_id,
            chunks=chunks,
            embeddings=embeddings,
            metadata_list=metadata_list
        )

        return FileIngestResponse(
            file_id=file_id,
            file_name=file.filename,
            file_type=file_type,
            chunks_created=len(chunks),
            storage_path=storage_path,
            status="ready"
        )

    except Exception as exc:
        logger.error(f"Ingestion failed for {file.filename}: {exc}", exc_info=True)
        # Update status to failed
        supabase.table("user_files").update({
            "status": "failed",
            "error_message": str(exc)
        }).eq("id", str(file_id)).execute()
        
        raise HTTPException(status_code=500, detail=f"Parsing or indexing failed: {exc}")
        
    finally:
        # Cleanup temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")


@router.post("/sample-data", response_model=FileIngestResponse)
async def ingest_sample_data(current_user: UserResponse = Depends(get_current_user)) -> FileIngestResponse:
    """
    Ingests standard CSV sample tooling catalog data (data/ai_tooling_catalog.csv).
    """
    logger.info("Sample catalog ingest requested.", extra={"user_id": str(current_user.id)})
    csv_path = "data/ai_tooling_catalog.csv"
    
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="Sample CSV catalog file not found.")
        
    with open(csv_path, "rb") as f:
        file_bytes = f.read()
        
    # Standard UploadFile packaging
    from fastapi import UploadFile
    import io
    
    upload_file = UploadFile(
        filename="ai_tooling_catalog.csv",
        file=io.BytesIO(file_bytes),
        size=len(file_bytes),
        headers={"content-type": "text/csv"}
    )
    
    # Delegate directly to our standard upload endpoint logic
    return await ingest_uploaded_file(file=upload_file, current_user=current_user)
