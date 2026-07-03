# services/vector_service.py
# This service coordinates pgvector storage operations and cosine similarity lookups.
# It interfaces directly with the document_chunks table and the match_document_chunks RPC.

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from app.services.supabase_service import SupabaseService
from app.models.file_models import ChunkResult
from app.config.settings import settings

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        self.supabase = SupabaseService.get_client()

    def store_chunks(
        self,
        user_id: UUID,
        file_id: UUID,
        chunks: List[str],
        embeddings: List[List[float]],
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """
        Pushes document text chunks and their dense embeddings into pgvector.
        Also updates the parent file record's chunk_count.
        """
        logger.info(
            f"Storing {len(chunks)} chunks in pgvector...",
            extra={"user_id": str(user_id), "file_id": str(file_id)}
        )
        
        if not chunks:
            return 0
            
        rows = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else {}
            
            # Extract fields for dedicated columns if present in metadata
            page_number = metadata.pop("page_number", None)
            section = metadata.pop("section", None)
            
            rows.append({
                "user_id": str(user_id),
                "file_id": str(file_id),
                "content": chunk,
                "embedding": embedding,
                "chunk_index": i,
                "page_number": int(page_number) if page_number is not None else None,
                "section": section,
                "metadata": metadata
            })

        # Insert chunks in batches of 100 to avoid request body size limits
        batch_size = 100
        inserted_count = 0
        for start_idx in range(0, len(rows), batch_size):
            batch = rows[start_idx:start_idx + batch_size]
            result = self.supabase.table("document_chunks").insert(batch).execute()
            inserted_count += len(result.data or [])

        # Update the parent file registry chunk_count
        self.supabase.table("user_files").update({
            "chunk_count": inserted_count,
            "status": "ready"
        }).eq("id", str(file_id)).execute()

        logger.info(f"Successfully stored {inserted_count} chunks in database.", extra={"file_id": str(file_id)})
        return inserted_count

    def search(
        self,
        user_id: UUID,
        query_embedding: List[float],
        top_k: int = 10,
        threshold: float = 0.0,
        file_ids: Optional[List[str]] = None
    ) -> List[ChunkResult]:
        """
        Queries similarity across pgvector using the match_document_chunks database function.
        Isolates searches to the calling user's files only.
        """
        logger.info(f"Executing pgvector similarity search... file_filter={file_ids}", extra={"user_id": str(user_id), "top_k": top_k})
        
        try:
            params = {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": top_k,
                "filter_user_id": str(user_id)
            }
            if file_ids is not None:
                params["filter_file_ids"] = file_ids

            res = self.supabase.rpc(
                "match_document_chunks",
                params
            ).execute()
            
            chunks = []
            for row in (res.data or []):
                chunks.append(ChunkResult(
                    chunk_id=UUID(row["id"]),
                    file_id=UUID(row["file_id"]),
                    file_name=row.get("file_name", "Unknown File"),
                    content=row["content"],
                    score=float(row["similarity"]),
                    page_number=row.get("page_number"),
                    section=row.get("section"),
                    chunk_index=row["chunk_index"]
                ))
            
            logger.info(f"Similarity search completed. Found {len(chunks)} results.", extra={"user_id": str(user_id)})
            return chunks
            
        except Exception as exc:
            logger.error(f"pgvector similarity query failed: {exc}", exc_info=True)
            raise RuntimeError(f"pgvector query failed: {exc}") from exc

    def delete_file_chunks(self, file_id: UUID) -> None:
        """
        Removes all chunks associated with a specific file.
        """
        logger.info(f"Deleting chunks from database: {file_id}")
        self.supabase.table("document_chunks").delete().eq("file_id", str(file_id)).execute()

    def get_user_chunk_count(self, user_id: UUID) -> int:
        """
        Returns the total number of document chunks indexed for a user.
        """
        res = self.supabase.table("document_chunks").select("id", count="exact").eq("user_id", str(user_id)).execute()
        return res.count or 0
