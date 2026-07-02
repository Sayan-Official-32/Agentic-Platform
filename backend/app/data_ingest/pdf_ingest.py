# data_ingest/pdf_ingest.py
# This module handles extracting text from Portable Document Format (PDF) files.
# It uses the PyPDF2 library, a standard Python library to parse PDF structures and extract text contents.
# It supports two ingestion styles: page-by-page chunking (each page becomes a document) or full merging.

import logging
from pathlib import Path
from typing import Dict, List

from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

def load_documents_from_pdf(file_path: str) -> List[Dict[str, str]]:
    """
    Extracts text content from a PDF file page-by-page.
    Each page becomes a separate document with associated metadata.
    
    Args:
        file_path: Path to the PDF file on disk.
        
    Returns:
        List[Dict[str, str]]: List of document dictionaries, ready to be indexed.
    """
    documents: List[Dict[str, str]] = []
    
    try:
        # 1. Instantiate the PdfReader to parse the PDF file structure
        pdf_reader = PdfReader(file_path)
        # 2. Extract the file name (without folder or extension) to use as the title base
        file_name = Path(file_path).stem
        # 3. Determine the total count of pages in the PDF
        total_pages = len(pdf_reader.pages)
        
        logger.info(f"Processing PDF: {file_name} with {total_pages} pages")
        
        # 4. Iterate through all pages in order, starting index at 1
        for page_num, page in enumerate(pdf_reader.pages, start=1):
            # Extract plain text from this page.
            text = page.extract_text()
            
            # If a page contains no text (e.g. it is scanned as an image), skip it.
            if not text or not text.strip():
                logger.warning(f"Skipping empty page {page_num} in {file_name}")
                continue
            
            text = text.strip()
            
            # Append page chunk to our list. We limit text size to 5000 characters to keep search index sizes reasonable.
            documents.append({
                "title": f"{file_name} - Page {page_num}",
                "snippet": text[:5000] if len(text) > 5000 else text,  
                "category": "pdf-document",
                "source": f"pdf-ingest:{file_name}",
                "page_number": str(page_num),
                "total_pages": str(total_pages),
                "file_name": file_name,
            })
        
        logger.info(f"Successfully extracted {len(documents)} pages from {file_name}")
        
    except Exception as e:
        logger.error(f"Error processing PDF {file_path}: {str(e)}")
        # Re-raise the exception so upstream coordinators are aware of the processing failure
        raise
    
    return documents

def load_documents_from_pdf_full_content(file_path: str) -> List[Dict[str, str]]:
    """
    Extracts and merges all text pages from a PDF into a single large document,
    rather than splitting it page-by-page.
    """
    documents: List[Dict[str, str]] = []
    
    try:
        pdf_reader = PdfReader(file_path)
        file_name = Path(file_path).stem
        total_pages = len(pdf_reader.pages)
        
        logger.info(f"Processing PDF as single document: {file_name} with {total_pages} pages")
        
        # Concatenate text from all valid pages separated by double newlines
        full_text = ""
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text and text.strip():
                full_text += text + "\n\n"
        
        # Save as a single combined document if any text was found
        if full_text.strip():
            documents.append({
                "title": file_name,
                "snippet": full_text.strip(),
                "category": "pdf-document",
                "source": f"pdf-ingest:{file_name}",
                "total_pages": str(total_pages),
                "file_name": file_name,
            })
            
            logger.info(f"Successfully extracted full content from {file_name}")
        else:
            logger.warning(f"No text content found in {file_name}")
        
    except Exception as e:
        logger.error(f"Error processing PDF {file_path}: {str(e)}")
        raise
    
    return documents