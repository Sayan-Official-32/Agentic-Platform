# services/reranker_service.py
# This service uses a SentenceTransformer CrossEncoder to rerank candidate chunks retrieved by vector search.
# A CrossEncoder computes attention simultaneously across both query and document text, 
# producing a significantly more accurate relevance score than cosine similarity alone.

import logging
from typing import List, Optional
from app.config.settings import settings
from app.models.file_models import ChunkResult

logger = logging.getLogger(__name__)

class RerankerService:
    _model = None

    def __init__(self):
        self.enabled = settings.reranker_enabled
        self.model_name = settings.reranker_model
        self.top_k = settings.reranker_top_k
        self._load_model()

    def _load_model(self):
        """Loads the CrossEncoder model if enabled and not already loaded."""
        if self.enabled and RerankerService._model is None:
            logger.info(f"Loading reranker model: {self.model_name}...")
            try:
                from sentence_transformers import CrossEncoder
                RerankerService._model = CrossEncoder(self.model_name)
                logger.info("Reranker model loaded successfully.")
            except Exception as exc:
                logger.error(f"Failed to load CrossEncoder reranker: {exc}", exc_info=True)
                # Keep service alive but disable to run fallback routing
                self.enabled = False

    def rerank(self, query: str, chunks: List[ChunkResult], top_k: Optional[int] = None) -> List[ChunkResult]:
        """
        Computes relevance scores for candidate chunks and sorts them.
        Returns the top_k reranked results.
        """
        if not chunks:
            return []

        limit = top_k if top_k is not None else self.top_k

        if not self.enabled or RerankerService._model is None:
            logger.info("Reranker is disabled or unavailable. Returning original vector ranking.")
            return chunks[:limit]

        logger.info(f"Reranking {len(chunks)} candidate chunks for query: '{query[:60]}...'")
        
        try:
            # 1. Format input pairs as [query, chunk_content]
            pairs = [[query, chunk.content] for chunk in chunks]
            
            # 2. Predict cross-encoder scores (higher score means more relevant)
            scores = RerankerService._model.predict(pairs)
            
            # 3. Inject scores and sort descending
            for chunk, score in zip(chunks, scores):
                chunk.rerank_score = float(score)
            
            sorted_chunks = sorted(chunks, key=lambda c: c.rerank_score or 0.0, reverse=True)
            
            logger.info(f"Reranking complete. Top score: {sorted_chunks[0].rerank_score:.4f}")
            return sorted_chunks[:limit]
            
        except Exception as exc:
            logger.error(f"Reranking failed: {exc}", exc_info=True)
            return chunks[:limit]
