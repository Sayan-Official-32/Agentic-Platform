# routers/files_router.py
# This module implements the file management endpoints.
# It allows users to view their uploaded files, check processing status, and delete documents.

import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from app.config.settings import settings
from app.dependencies.auth_dependencies import get_current_user
from app.models.auth_models import UserResponse
from app.models.file_models import UserFileResponse
from app.services.supabase_service import SupabaseService
from app.services.storage_service import StorageService
from app.services.vector_service import VectorService

router = APIRouter(prefix=settings.api_prefix + "/files", tags=["files"])
logger = logging.getLogger(__name__)

supabase = SupabaseService.get_client()
storage_service = StorageService()
vector_service = VectorService()

@router.get("", response_model=List[UserFileResponse])
def list_user_files(current_user: UserResponse = Depends(get_current_user)) -> List[UserFileResponse]:
    """
    Lists all files uploaded by the authenticated user.
    """
    logger.info("Listing user files...", extra={"user_id": str(current_user.id)})
    try:
        res = supabase.table("user_files").select("*").eq("user_id", str(current_user.id)).order("created_at", desc=True).execute()
        
        files = []
        for row in (res.data or []):
            files.append(UserFileResponse(
                id=UUID(row["id"]),
                file_name=row["file_name"],
                file_type=row["file_type"],
                status=row["status"],
                chunk_count=row.get("chunk_count", 0),
                file_size=row.get("file_size"),
                suggested_questions=row.get("suggested_questions"),
                conversation_id=UUID(row["conversation_id"]) if row.get("conversation_id") else None,
                created_at=row["created_at"]
            ))
        return files
    except Exception as exc:
        logger.error(f"Failed to list user files: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error during listing.")

@router.get("/{file_id}", response_model=UserFileResponse)
def get_user_file(file_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> UserFileResponse:
    """
    Retrieves the status and metadata of a specific file.
    """
    logger.info(f"Retrieving user file: {file_id}", extra={"user_id": str(current_user.id)})
    try:
        res = supabase.table("user_files").select("*").eq("id", str(file_id)).eq("user_id", str(current_user.id)).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="File not found or access denied.")
            
        row = res.data[0]
        return UserFileResponse(
            id=UUID(row["id"]),
            file_name=row["file_name"],
            file_type=row["file_type"],
            status=row["status"],
            chunk_count=row.get("chunk_count", 0),
            file_size=row.get("file_size"),
            suggested_questions=row.get("suggested_questions"),
            conversation_id=UUID(row["conversation_id"]) if row.get("conversation_id") else None,
            created_at=row["created_at"]
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to retrieve user file: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error during retrieval.")

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_file(file_id: UUID, current_user: UserResponse = Depends(get_current_user)):
    """
    Deletes a file, its corresponding text chunks, and its Supabase Storage object.
    """
    logger.info(f"Request to delete user file: {file_id}", extra={"user_id": str(current_user.id)})
    try:
        # 1. Fetch file to verify ownership and retrieve storage_path
        res = supabase.table("user_files").select("*").eq("id", str(file_id)).eq("user_id", str(current_user.id)).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="File not found or access denied.")
            
        row = res.data[0]
        storage_path = row["storage_path"]
        
        # 2. Delete pgvector text chunks
        vector_service.delete_file_chunks(file_id)
        
        # 3. Delete from Supabase Storage
        storage_service.delete_file(storage_path)
        
        # 4. Delete the file metadata record
        supabase.table("user_files").delete().eq("id", str(file_id)).execute()
        
        logger.info(f"Successfully deleted file: {file_id}", extra={"user_id": str(current_user.id)})
        return
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to delete file: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error during deletion.")
