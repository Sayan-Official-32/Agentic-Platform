# data_ingest/chunker.py
# This module implements text chunking algorithms with configurable overlap settings.
# Overlapping chunks prevent text context loss at the boundaries of adjacent chunks.

import logging
from typing import List
from app.config.settings import settings

logger = logging.getLogger(__name__)

def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """
    Splits text into overlapping character-based chunks.
    
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

    chunks = []
    text = text.strip()
    if not text:
        return chunks

    text_len = len(text)
    step = chunk_size - overlap
    
    start = 0
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start index forward. Stop if we have reached or exceeded the end of the text.
        if end == text_len:
            break
        start += step

    return chunks
