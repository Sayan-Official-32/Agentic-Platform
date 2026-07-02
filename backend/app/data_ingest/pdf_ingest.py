# data_ingest/pdf_ingest.py
# This module handles extracting text from Portable Document Format (PDF) files.
# It uses the PyPDF2 library to parse PDF structures and extract text contents.
# Each page becomes a separate document unit with associated page number metadata.

import logging
from pathlib import Path
from typing import Dict, Any, List
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

def load_documents_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    """
    Extracts text content from a PDF file page-by-page.
    Each page's text is returned along with page number metadata.
    """
    documents: List[Dict[str, Any]] = []
    
    try:
        pdf_reader = PdfReader(file_path)
        file_name = Path(file_path).stem
        total_pages = len(pdf_reader.pages)
        
        logger.info(f"Processing PDF: {file_name} with {total_pages} pages")
        
        for page_num, page in enumerate(pdf_reader.pages, start=1):
            text = page.extract_text()
            
            if not text or not text.strip():
                logger.warning(f"Skipping empty page {page_num} in {file_name}")
                continue
            
            documents.append({
                "content": text.strip(),
                "metadata": {
                    "page_number": page_num,
                    "total_pages": total_pages,
                    "file_name": file_name
                }
            })
        
        logger.info(f"Successfully extracted {len(documents)} pages from {file_name}")
        
    except Exception as e:
        logger.error(f"Error processing PDF {file_path}: {str(e)}")
        raise
    
    return documents