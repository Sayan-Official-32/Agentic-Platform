# services/search_service.py
# This module implements the SearchService class.
# Elasticsearch is an enterprise-grade search engine based on the Lucene search library.
# It allows fast full-text searching, text relevance scoring, and indexing of unstructured snippets.
# Here, we use Elasticsearch to store and retrieve document paragraphs to support RAG (Retrieval Augmented Generation).

import logging
from typing import Any, Dict, List

from app.config.settings import settings
from app.models.chat_models import SearchResult

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self) -> None:
        self.url = settings.elasticsearch_url
        self.index_name = settings.elasticsearch_index
        self.api_key = settings.elasticsearch_api_key
        self._client = None
        self._connect()

    def _connect(self) -> None:
        """
        Dynamically imports the 'elasticsearch' module and connects to the cluster.
        Using basic auth or API keys for validation.
        """
        if self._client is not None:
            return
        try:
            import importlib

            # Dynamically import Elasticsearch driver
            elasticsearch_module = importlib.import_module("elasticsearch")
            elasticsearch_class = getattr(elasticsearch_module, "Elasticsearch")
            
            connection_params = {
                "hosts": [self.url],
                "verify_certs": False,  # Turn off TLS certificate verification for local docker/dev setups
                "ssl_show_warn": False,  # Suppress security warnings in console logs
            }
            
            # Hook in security credentials
            if self.api_key:
                connection_params["api_key"] = self.api_key
            elif settings.elasticsearch_user and settings.elasticsearch_password:
                connection_params["basic_auth"] = (
                    settings.elasticsearch_user,
                    settings.elasticsearch_password
                )
            
            client = elasticsearch_class(**connection_params)
            # Fetch cluster information to verify connection is successful
            info = client.info()
            self._client = client
            logger.info(
                "Elasticsearch client initialized.",
                extra={
                    "index_name": self.index_name,
                    "url": self.url,
                    "version": info.get("version", {}).get("number", "unknown")
                },
            )
        except Exception as exc:
            logger.debug(
                "Elasticsearch connection attempt failed.",
                extra={"index_name": self.index_name, "url": self.url, "reason": str(exc)},
            )
            self._client = None
            
    def ensure_index(self) -> None:
        """
        Checks if the index exists in Elasticsearch. If not, it creates it with specific field mappings.
        - 'text' fields (like title, snippet) are broken down into tokens for full-text search.
        - 'keyword' fields (like category, source) are indexed as exact values (great for filtering/sorting).
        """
        self._connect()
        if not self._client:
            raise RuntimeError("Elasticsearch is not available.")
        # If the index does not exist, create it
        if not self._client.indices.exists(index=self.index_name):
            logger.info("Creating Elasticsearch index.", extra={"index_name": self.index_name})
            self._client.indices.create(
                index=self.index_name,
                mappings={
                    "properties": {
                        "title": {"type": "text"},
                        "snippet": {"type": "text"},
                        "category": {"type": "keyword"},
                        "source": {"type": "keyword"},
                        "page_number": {"type": "integer"},
                        "total_pages": {"type": "integer"},
                        "file_name": {"type": "keyword"},
                    }
                },
            )
            
    def bulk_index_documents(self, documents: List[Dict[str, Any]]) -> int:
        """
        Uses Elasticsearch's bulk endpoint to index multiple documents in a single HTTP request.
        Bulk indexing is substantially faster than pushing documents one by one.
        """
        self._connect()
        if not self._client:
            raise RuntimeError("Elasticsearch is not available.")
        logger.info(
            "Bulk index started.",
            extra={"index_name": self.index_name, "document_count": len(documents)},
        )
        self.ensure_index()
        
        # Elasticsearch bulk API format requires alternating lines:
        # Line 1: {"index": {"_index": "index_name"}}
        # Line 2: { "field1": "value1", ... } (the actual document)
        operations: List[Dict[str, Any]] = []
        for document in documents:
            operations.append({"index": {"_index": self.index_name}})
            operations.append(document)
            
        # Push to Elasticsearch. refresh=True makes changes immediately searchable.
        response = self._client.bulk(operations=operations, refresh=True)
        if response.get("errors"):
            logger.error("Bulk indexing completed with errors.", extra={"index_name": self.index_name})
            raise RuntimeError("Bulk indexing completed with errors.")
        logger.info(
            "Bulk index completed.",
            extra={"index_name": self.index_name, "document_count": len(documents)},
        )
        return len(documents)
    
    async def search(self, query: str) -> List[SearchResult]:
        """
        Searches the Elasticsearch index for matching snippets.
        Uses a 'multi_match' query which scans title, snippet, and category fields.
        'title^2' applies a weight/boost factor of 2, making keyword matches in the title twice as important.
        """
        self._connect()
        if not self._client:
            raise RuntimeError("Elasticsearch is not available. Please ingest data and start Elasticsearch.")
        logger.info(
            "Elasticsearch query started.",
            extra={"index_name": self.index_name, "query_preview": query[:120]},
        )
        try:
            response = self._client.search(
                index=self.index_name,
                query={
                    "multi_match": {
                        "query": query,
                        # fields specifies fields to query. ^2 applies weight multiplication to relevance score.
                        "fields": ["title^2", "snippet", "category"],
                    }
                },
                size=5, # Limit query returns to top 5 hits
            )
            hits = response.get("hits", {}).get("hits", [])
            logger.info(
                "Elasticsearch query completed.",
                extra={"index_name": self.index_name, "hits_count": len(hits)},
            )
            # Map raw Elasticsearch result dicts into structured SearchResult schemas
            return [
                SearchResult(
                    title=hit.get("_source", {}).get("title", "Untitled"),
                    snippet=hit.get("_source", {}).get("snippet", ""),
                    score=float(hit.get("_score", 0.0)), # Relevance score assigned by ES scoring algorithms
                    source=hit.get("_source", {}).get("source", "elasticsearch"),
                    page_number=hit.get("_source", {}).get("page_number"),
                    file_name=hit.get("_source", {}).get("file_name"),
                )
                for hit in hits
            ]
        except Exception as exc:
            logger.exception(
                "Elasticsearch query failed.",
                extra={"index_name": self.index_name, "query_preview": query[:120]},
            )
            raise RuntimeError(f"Elasticsearch query failed: {exc}") from exc
        
    @property
    def available(self) -> bool:
        """Indicates whether the Elasticsearch server is reachable."""
        self._connect()
        return self._client is not None