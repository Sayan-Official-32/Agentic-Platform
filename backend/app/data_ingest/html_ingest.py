# data_ingest/html_ingest.py
# Parses HTML documents (.html, .htm) using beautifulsoup4 and the lxml parser backend.

import logging
from typing import List

logger = logging.getLogger(__name__)

def load_documents_from_html(file_path: str) -> List[str]:
    """
    Extracts text paragraphs from an HTML file, stripping script and style tags.
    """
    try:
        from bs4 import BeautifulSoup
        
        # Read HTML file (supporting UTF-8 and Latin-1 fallbacks)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="iso-8859-1") as f:
                html_content = f.read()

        soup = BeautifulSoup(html_content, "lxml")
        
        # Strip script and style blocks
        for element in soup(["script", "style", "meta", "noscript", "header", "footer"]):
            element.decompose()
            
        # Get readable text block
        text = soup.get_text()
        
        # Clean lines
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into individual lines, strip spaces, drop empty lines
        chunks = [line for line in lines if line]
        
        logger.info(f"Extracted {len(chunks)} text lines from HTML: {file_path}")
        return chunks
    except Exception as exc:
        logger.error(f"Error parsing HTML file {file_path}: {exc}")
        raise
