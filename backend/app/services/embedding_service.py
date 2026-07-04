# services/embedding_service.py
# This service generates dense vector embeddings for text snippets using sentence-transformers.
# It caches generated embeddings in Redis (24h TTL) to minimize redundant CPU calculations.

import hashlib
import json
import logging
from typing import List
from app.config.settings import settings
from app.memory.redis_memory import RedisMemoryService

logger = logging.getLogger(__name__)

class EmbeddingService:
    _model = None

    def __init__(self):
        self.model_name = settings.embedding_model
        self.cache_ttl = settings.embedding_cache_ttl
        # Share Redis connection from settings configuration
        self.cache = RedisMemoryService(settings.redis_url, settings.redis_ttl_seconds)

    def _load_model(self):
        """Loads the SentenceTransformer model into memory if not already loaded."""
        if EmbeddingService._model is None:
            logger.info(f"Loading embedding model: {self.model_name}...")
            try:
                from sentence_transformers import SentenceTransformer
                try:
                    # Try loading from local cache first to avoid network checks
                    EmbeddingService._model = SentenceTransformer(self.model_name, local_files_only=True)
                    logger.info("Embedding model loaded from local files successfully.")
                except Exception:
                    logger.info(f"Model {self.model_name} not found locally or needs update, downloading from HF Hub...")
                    EmbeddingService._model = SentenceTransformer(self.model_name, local_files_only=False)
                    logger.info("Embedding model downloaded and loaded successfully.")
            except Exception as exc:
                logger.error(f"Failed to load sentence-transformers: {exc}", exc_info=True)
                raise RuntimeError("Could not load embedding transformer.") from exc

    def _get_cache_key(self, text: str) -> str:
        """Generates a unique cache key for a given text snippet."""
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"embed:{text_hash}"

    def embed_text(self, text: str) -> List[float]:
        """
        Generates a 384-dimensional vector embedding for a text snippet.
        Checks the Redis cache first.
        """
        if not text or not text.strip():
            return [0.0] * settings.embedding_dims

        cache_key = self._get_cache_key(text)
        
        # 1. Attempt to retrieve from Redis cache
        try:
            cached_val = self.cache.get_value(cache_key)
            if cached_val:
                return json.loads(cached_val)
        except Exception as exc:
            logger.debug(f"Redis cache read error for embedding: {exc}")

        # Ensure model is loaded before inference
        self._load_model()

        # 2. Cache miss: run model inference
        vector = EmbeddingService._model.encode(text).tolist()
        
        # 3. Store result in Redis cache
        try:
            self.cache.set_value(cache_key, json.dumps(vector), ttl=self.cache_ttl)
        except Exception as exc:
            logger.debug(f"Redis cache write error for embedding: {exc}")

        return vector

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of texts in batch. Utilizes cache mapping where possible.
        """
        results: List[List[float] | None] = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []

        # 1. Check cache for all texts
        for i, text in enumerate(texts):
            if not text or not text.strip():
                results[i] = [0.0] * settings.embedding_dims
                continue

            cache_key = self._get_cache_key(text)
            try:
                cached_val = self.cache.get_value(cache_key)
                if cached_val:
                    results[i] = json.loads(cached_val)
                    continue
            except Exception:
                pass
            
            uncached_indices.append(i)
            uncached_texts.append(text)

        # 2. Run inference for uncached texts in batch
        if uncached_texts:
            logger.info(f"Computing embeddings for {len(uncached_texts)} uncached chunks.")
            # Ensure model is loaded before inference
            self._load_model()
            vectors = EmbeddingService._model.encode(uncached_texts).tolist()
            
            for index, vector, text in zip(uncached_indices, vectors, uncached_texts):
                results[index] = vector
                # Cache the new vector
                cache_key = self._get_cache_key(text)
                try:
                    self.cache.set_value(cache_key, json.dumps(vector), ttl=self.cache_ttl)
                except Exception:
                    pass

        return [res for res in results if res is not None]
