# data_ingest/md_ingest.py
# Parses Markdown (.md) documents, cleaning markdown decorators like titles, lists, and links.

import logging
import re
from typing import List

logger = logging.getLogger(__name__)

def load_documents_from_md(file_path: str) -> List[str]:
    """
    Extracts text blocks from a Markdown file, cleaning headers, links, and styling.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Clean links: [link text](url) -> link text
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        
        # Clean headers: # Header -> Header
        content = re.sub(r'#+\s+(.+)', r'\1', content)
        
        # Clean inline formatting: **bold** or *italic* -> text
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
        content = re.sub(r'\*([^*]+)\*', r'\1', content)
        
        # Clean horizontal rules
        content = re.sub(r'^-{3,}\s*$', '', content, flags=re.MULTILINE)

        # Split by double newline to get logical paragraphs
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        
        logger.info(f"Extracted {len(paragraphs)} paragraphs from Markdown: {file_path}")
        return paragraphs
    except Exception as exc:
        logger.error(f"Error parsing Markdown file {file_path}: {exc}")
        raise
