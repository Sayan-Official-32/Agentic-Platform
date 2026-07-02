import logging
from typing import List, Optional
from uuid import UUID

from app.config.settings import settings
from app.models.chat_models import SearchResult
from app.services.vector_service import VectorService
from app.services.embedding_service import EmbeddingService
from app.services.reranker_service import RerankerService

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self) -> None:
        self.index_name = settings.elasticsearch_index
        self.vector_service = VectorService()
        self.embedding_service = EmbeddingService()
        self.reranker_service = RerankerService()

    async def search(self, query: str, user_id: Optional[UUID] = None) -> List[SearchResult]:
        """
        Executes a vector similarity search scoped to the user ID, reranks results, and maps to SearchResult.
        """
        if not user_id:
            logger.warning("Search executed without a user_id. Returning empty results.")
            return []

        logger.info(f"Compatibility search query received: '{query[:60]}' for user {user_id}")
        
        try:
            # 1. Compute embedding for the query text
            query_vector = self.embedding_service.embed_text(query)
            
            # 2. Perform the similarity search using pgvector (request top_k candidates)
            chunks = self.vector_service.search(
                user_id=user_id,
                query_embedding=query_vector,
                top_k=settings.vector_top_k
            )
            
            # 3. Rerank retrieved candidate chunks
            reranked_chunks = self.reranker_service.rerank(query, chunks)
            
            # 4. Map ChunkResult models to SearchResult compatibility models
            results = []
            for chunk in reranked_chunks:
                results.append(SearchResult(
                    title=chunk.file_name,
                    snippet=chunk.content,
                    score=chunk.rerank_score if chunk.rerank_score is not None else chunk.score,
                    source="pgvector",
                    page_number=chunk.page_number,
                    file_name=chunk.file_name
                ))
                
            return results
        except Exception as exc:
            logger.error(f"Compatibility search failed: {exc}", exc_info=True)
            return []

    @property
    def available(self) -> bool:
        """Indicates database connectivity (checks Supabase connection client status)."""
        try:
            return self.vector_service.supabase is not None
        except Exception:
            return False