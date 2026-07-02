# data_ingest/file_ingest.py
# This module acts as the router/orchestrator for file ingestion.
# It detects the file type (PDF vs. CSV) based on its suffix and routes it to the appropriate sub-parser,
# and supports bulk scanning a directory recursively or non-recursively.

import logging
from pathlib import Path
from typing import Dict, List, Literal

from app.data_ingest.csv_ingest import load_documents_from_csv
from app.data_ingest.pdf_ingest import load_documents_from_pdf

logger = logging.getLogger(__name__)

# FileType limits valid strings to either "pdf" or "csv"
FileType = Literal["pdf", "csv"]


def detect_file_type(file_path: str) -> FileType:
    """
    Looks at a file's extension to determine if it is a PDF or CSV.
    """
    suffix = Path(file_path).suffix.lower()
    
    if suffix == ".pdf":
        return "pdf"
    elif suffix == ".csv":
        return "csv"
    else:
        # If the format is not supported, raise a ValueError to prevent processing
        raise ValueError(f"Unsupported file type: {suffix}. Supported types: .pdf, .csv")


def load_documents_from_file(file_path: str, file_type: FileType | None = None) -> List[Dict[str, str]]:
    """
    Loads documents from a single file by auto-detecting its type and calling the appropriate loader.
    """
    file_path_obj = Path(file_path)
    
    # 1. Verify that the file actually exists on the filesystem
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # 2. Detect the type if not explicitly passed
    if file_type is None:
        file_type = detect_file_type(file_path)
    
    logger.info(f"Loading documents from {file_type.upper()} file: {file_path}")
    
    # 3. Route to the correct sub-parser
    if file_type == "pdf":
        return load_documents_from_pdf(file_path)
    elif file_type == "csv":
        return load_documents_from_csv(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def load_documents_from_directory(
    directory_path: str,
    file_types: List[FileType] | None = None,
    recursive: bool = False
) -> Dict[str, List[Dict[str, str]]]:
    """
    Scans a directory for PDF and CSV files and processes all of them in a batch.
    
    Args:
        directory_path: Absolute or relative directory path to search.
        file_types: List of file extensions to search for (defaults to both PDF and CSV).
        recursive: If True, searches child subfolders; otherwise only matches files directly in this folder.
        
    Returns:
        Dict[str, List[Dict[str, str]]]: Maps file paths -> list of structured document snippets extracted.
    """
    dir_path = Path(directory_path)
    
    # Validate that path exists and is a directory
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    if not dir_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory_path}")
    
    if file_types is None:
        file_types = ["pdf", "csv"]
    
    results: Dict[str, List[Dict[str, str]]] = {}
    
    # Set search glob patterns based on requested extensions
    patterns = []
    if "pdf" in file_types:
        patterns.append("*.pdf")
    if "csv" in file_types:
        patterns.append("*.csv")
    
    # Process files matching the patterns
    for pattern in patterns:
        # rglob searches recursively, glob searches only top level directory
        if recursive:
            files = dir_path.rglob(pattern)
        else:
            files = dir_path.glob(pattern)
        
        for file_path in files:
            try:
                logger.info(f"Processing file: {file_path}")
                # Load the items
                documents = load_documents_from_file(str(file_path))
                results[str(file_path)] = documents
                logger.info(f"Successfully loaded {len(documents)} documents from {file_path.name}")
            except Exception as e:
                # Log error and continue so one broken file doesn't crash the entire batch import
                logger.error(f"Error processing file {file_path}: {str(e)}")
                continue
    
    total_docs = sum(len(docs) for docs in results.values())
    logger.info(f"Loaded {total_docs} total documents from {len(results)} files in {directory_path}")
    
    return results


def get_supported_file_types() -> List[str]:
    """Returns lists of supported extensions for UI hints."""
    return [".pdf", ".csv"]