# data_ingest/chunker.py
# This module implements text chunking algorithms with configurable overlap settings.
# Uses LangChain's RecursiveCharacterTextSplitter to intelligently chunk text.

import logging
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config.settings import settings

logger = logging.getLogger(__name__)

def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """
    Splits text into overlapping character-based chunks using LangChain.
    
    Args:
        text: Raw text to split.
        chunk_size: Size of each chunk in characters.
        overlap: Character overlap between consecutive chunks.
    """
    if chunk_size is None:
        chunk_size = settings.chunk_size
    if overlap is None:
        overlap = settings.chunk_overlap

    if overlap >= chunk_size:
        logger.warning(f"Overlap ({overlap}) >= Chunk Size ({chunk_size}). Resetting overlap to 10% of size.")
        overlap = chunk_size // 10

    if not text or not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks = splitter.split_text(text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]
