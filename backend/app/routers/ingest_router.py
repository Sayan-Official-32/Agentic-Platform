# routers/ingest_router.py
# This module implements the file ingestion API routes.
# It processes files (PDF, DOCX, TXT, CSV, XLSX, PPTX, HTML, JSON, MD),
# uploads them to Supabase Storage, chunks them, computes embeddings, and stores them in pgvector.

import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional
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
    conversation_id: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user)
) -> FileIngestResponse:
    """
    Ingests an uploaded file: saves metadata, uploads to Storage, chunks text,
    embeds, and stores in pgvector.
    """
    logger.info(f"Ingesting file: {file.filename} for conversation: {conversation_id}", extra={"user_id": str(current_user.id)})
    
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
            "status": "processing",
            "conversation_id": conversation_id if conversation_id else None
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

        # Generate sample questions from the parsed text
        import re
        sample_text = ""
        for doc in documents[:2]:
            sample_text += doc.get("content", "") + "\n"
            if len(sample_text) > 1500:
                break
        
        suggested_questions = []
        if sample_text.strip():
            try:
                from app.services.llm_service import LLMService
                llm_service = LLMService()
                prompt = (
                    "Below is a short snippet from a newly uploaded document. "
                    "Generate exactly 3 short, specific, and interesting questions that a user might want to ask about this document. "
                    "Respond with ONLY the questions, one per line. Do not add numbers, bullet points, introductory text, or blank lines.\n\n"
                    f"Document Snippet:\n{sample_text[:1500]}"
                )
                llm_response = await llm_service.generate(prompt)
                lines = [line.strip("-*• ").strip() for line in llm_response.split("\n")]
                cleaned_lines = []
                for line in lines:
                    cleaned = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
                    if cleaned and len(cleaned) > 10:
                        cleaned_lines.append(cleaned)
                suggested_questions = cleaned_lines[:3]
            except Exception as llm_exc:
                logger.warning(f"Failed to generate suggested questions: {llm_exc}")
                suggested_questions = []

        if suggested_questions:
            try:
                supabase.table("user_files").update({
                    "suggested_questions": suggested_questions
                }).eq("id", str(file_id)).execute()
            except Exception as e:
                logger.error(f"Failed to save suggested questions to DB: {e}")

        # Link file to conversation if id was provided
        valid_conv_uuid = None
        if conversation_id and conversation_id.strip() and conversation_id.strip().lower() not in ("null", "undefined"):
            try:
                valid_conv_uuid = uuid.UUID(conversation_id.strip())
            except ValueError:
                logger.error(f"Invalid conversation_id UUID format: {conversation_id}")

        if valid_conv_uuid:
            try:
                conv_res = supabase.table("conversation_sessions").select("file_ids").eq("id", str(valid_conv_uuid)).execute()
                if conv_res.data:
                    current_file_ids = conv_res.data[0].get("file_ids") or []
                    if str(file_id) not in current_file_ids:
                        new_file_ids = current_file_ids + [str(file_id)]
                        supabase.table("conversation_sessions").update({
                            "file_ids": new_file_ids
                        }).eq("id", str(valid_conv_uuid)).execute()
            except Exception as e:
                logger.error(f"Failed to append file to conversation: {e}")

        return FileIngestResponse(
            file_id=file_id,
            file_name=file.filename,
            file_type=file_type,
            chunks_created=len(chunks),
            storage_path=storage_path,
            status="ready",
            suggested_questions=suggested_questions,
            conversation_id=valid_conv_uuid
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
