# data_ingest/txt_ingest.py
# Parses plain text (.txt) files.

import logging
from typing import List

logger = logging.getLogger(__name__)

def load_documents_from_txt(file_path: str) -> List[str]:
    """
    Extracts raw lines/paragraphs from a plain text file.
    """
    try:
        # Try reading as UTF-8 first
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback to ISO-8859-1 (Latin-1)
            logger.warning(f"UTF-8 decode failed for {file_path}, falling back to ISO-8859-1.")
            with open(file_path, "r", encoding="iso-8859-1") as f:
                content = f.read()
                
        # Split by double newlines or single newlines to get logical blocks
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        if not paragraphs and content.strip():
            # If split on double newline returned nothing, fall back to lines
            paragraphs = [line.strip() for line in content.split("\n") if line.strip()]
            
        logger.info(f"Extracted {len(paragraphs)} text blocks from TXT file: {file_path}")
        return paragraphs
    except Exception as exc:
        logger.error(f"Error parsing TXT file {file_path}: {exc}")
        raise
