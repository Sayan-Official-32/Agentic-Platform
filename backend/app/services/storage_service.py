# services/storage_service.py
# This service interacts with Supabase Storage to manage user-uploaded files.
# It creates private paths scoped by user ID and file ID to prevent cross-user access.

import logging
from typing import Union
from app.services.supabase_service import SupabaseService
from app.config.settings import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.supabase = SupabaseService.get_client()
        self.bucket_name = settings.supabase_storage_bucket

    def upload_file(self, user_id: str, file_id: str, filename: str, file_bytes: bytes) -> str:
        """
        Uploads file bytes to a private Supabase Storage path.
        Returns the relative storage path inside the bucket.
        """
        # Define user-scoped path structure
        storage_path = f"{user_id}/{file_id}/{filename}"
        logger.info(
            f"Uploading file bytes to Supabase Storage: {storage_path}",
            extra={"user_id": user_id, "file_id": file_id, "file_name": filename}
        )
        
        try:
            import gzip
            compressed_bytes = gzip.compress(file_bytes)
            logger.info(
                f"Compressed storage file: original_size={len(file_bytes)} -> compressed_size={len(compressed_bytes)}",
                extra={"user_id": user_id, "file_id": file_id, "file_name": filename}
            )

            # Upload compressed file. Overwrite existing if any conflict.
            self.supabase.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=compressed_bytes,
                file_options={
                    "cache-control": "3600",
                    "upsert": "true",
                    "content-encoding": "gzip"
                }
            )
            return storage_path
        except Exception as exc:
            logger.error(f"Supabase Storage upload failed: {exc}", exc_info=True)
            raise RuntimeError(f"Storage upload failed: {exc}") from exc

    def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """
        Generates a temporary signed URL to safely read/download the file.
        """
        try:
            res = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                path=storage_path,
                expires_in=expires_in
            )
            return res.get("signedURL") or res.get("signedUrl") or ""
        except Exception as exc:
            logger.error(f"Failed to generate signed URL for {storage_path}: {exc}")
            return ""

    def delete_file(self, storage_path: str) -> None:
        """
        Removes a file from the bucket.
        """
        logger.info(f"Removing file from Supabase Storage: {storage_path}")
        try:
            self.supabase.storage.from_(self.bucket_name).remove([storage_path])
        except Exception as exc:
            logger.warning(f"Failed to delete storage path {storage_path}: {exc}")
