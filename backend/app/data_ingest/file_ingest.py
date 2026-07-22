# data_ingest/file_ingest.py
# This module acts as the router/orchestrator for file ingestion.
# Uses LangChain's Document Loaders to automatically parse and extract text from files.

import logging
from pathlib import Path
from typing import Dict, List, Any, Literal

from langchain_community.document_loaders import (
    PyPDFLoader,
    CSVLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredExcelLoader,
    UnstructuredPowerPointLoader,
    BSHTMLLoader,
    UnstructuredMarkdownLoader,
)

logger = logging.getLogger(__name__)

FileType = Literal["pdf", "csv", "docx", "txt", "xlsx", "pptx", "html", "json", "md"]

def detect_file_type(file_path: str) -> FileType:
    """
    Detects the file type from its extension suffix.
    """
    suffix = Path(file_path).suffix.lower()
    
    type_map = {
        ".pdf": "pdf",
        ".csv": "csv",
        ".docx": "docx",
        ".txt": "txt",
        ".xlsx": "xlsx",
        ".pptx": "pptx",
        ".html": "html",
        ".htm": "html",
        ".json": "json",
        ".md": "md"
    }
    
    if suffix in type_map:
        return type_map[suffix]
    else:
        raise ValueError(
            f"Unsupported file type: {suffix}. Supported types: "
            ".pdf, .csv, .docx, .txt, .xlsx, .pptx, .html, .json, .md"
        )

def load_documents_from_file(file_path: str, file_type: FileType | None = None) -> List[Dict[str, Any]]:
    """
    Loads documents from a single file using LangChain document loaders.
    Always returns a list of dictionaries with structure: {"content": str, "metadata": dict}.
    """
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if file_type is None:
        file_type = detect_file_type(file_path)
    
    logger.info(f"Routing to LangChain parser for {file_type.upper()} file: {file_path}")
    
    try:
        if file_type == "pdf":
            loader = PyPDFLoader(file_path)
        elif file_type == "csv":
            loader = CSVLoader(file_path)
        elif file_type == "docx":
            loader = Docx2txtLoader(file_path)
        elif file_type in ("txt", "json"):
            # Use TextLoader for raw text and json objects without explicit schema
            loader = TextLoader(file_path)
        elif file_type == "xlsx":
            loader = UnstructuredExcelLoader(file_path)
        elif file_type == "pptx":
            loader = UnstructuredPowerPointLoader(file_path)
        elif file_type == "html":
            loader = BSHTMLLoader(file_path)
        elif file_type == "md":
            loader = UnstructuredMarkdownLoader(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
            
        # Execute LangChain loader
        docs = loader.load()
        
        # Convert LangChain Document objects to our unified dict structure
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in docs
        ]
        
    except Exception as exc:
        logger.error(f"LangChain loader failed for {file_path}: {exc}")
        raise

def load_documents_from_directory(
    directory_path: str,
    file_types: List[FileType] | None = None,
    recursive: bool = False
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Scans a directory for files of supported formats and parses them in a batch.
    """
    dir_path = Path(directory_path)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    if not dir_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory_path}")
    
    if file_types is None:
        file_types = ["pdf", "csv", "docx", "txt", "xlsx", "pptx", "html", "json", "md"]
        
    results: Dict[str, List[Dict[str, Any]]] = {}
    
    glob_patterns = {
        "pdf": "*.pdf",
        "csv": "*.csv",
        "docx": "*.docx",
        "txt": "*.txt",
        "xlsx": "*.xlsx",
        "pptx": "*.pptx",
        "html": "*.html",
        "json": "*.json",
        "md": "*.md"
    }
    
    patterns = [glob_patterns[t] for t in file_types if t in glob_patterns]
    
    for pattern in patterns:
        files = dir_path.rglob(pattern) if recursive else dir_path.glob(pattern)
        for file_path in files:
            try:
                documents = load_documents_from_file(str(file_path))
                results[str(file_path)] = documents
                logger.info(f"Loaded {len(documents)} document sections from {file_path.name}")
            except Exception as e:
                logger.error(f"Error parsing file {file_path}: {e}")
                continue
                
    total_docs = sum(len(docs) for docs in results.values())
    logger.info(f"Loaded {total_docs} total documents from {len(results)} files in {directory_path}")
    return results

def get_supported_file_types() -> List[str]:
    return [".pdf", ".csv", ".docx", ".txt", ".xlsx", ".pptx", ".html", ".json", ".md"]