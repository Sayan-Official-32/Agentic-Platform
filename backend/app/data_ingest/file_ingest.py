# data_ingest/file_ingest.py
# This module acts as the router/orchestrator for file ingestion.
# It detects the file type (out of 9 supported extensions) and routes it to the correct parser,
# mapping all inputs to a unified {"content": str, "metadata": dict} structure.

import logging
from pathlib import Path
from typing import Dict, List, Any, Literal

from app.data_ingest.csv_ingest import load_documents_from_csv
from app.data_ingest.pdf_ingest import load_documents_from_pdf

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
    Loads documents from a single file by auto-detecting its type and calling the appropriate loader.
    Always returns a list of dictionaries with structure: {"content": str, "metadata": dict}.
    """
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if file_type is None:
        file_type = detect_file_type(file_path)
    
    logger.info(f"Routing to parser for {file_type.upper()} file: {file_path}")
    
    if file_type == "pdf":
        return load_documents_from_pdf(file_path)
        
    elif file_type == "csv":
        raw = load_documents_from_csv(file_path)
        return [
            {
                "content": item["snippet"],
                "metadata": {
                    "title": item["title"],
                    "category": item["category"],
                    "source": item["source"]
                }
            }
            for item in raw
        ]
        
    elif file_type == "docx":
        from app.data_ingest.docx_ingest import load_documents_from_docx
        texts = load_documents_from_docx(file_path)
        return [{"content": text, "metadata": {}} for text in texts]
        
    elif file_type == "txt":
        from app.data_ingest.txt_ingest import load_documents_from_txt
        texts = load_documents_from_txt(file_path)
        return [{"content": text, "metadata": {}} for text in texts]
        
    elif file_type == "xlsx":
        from app.data_ingest.xlsx_ingest import load_documents_from_xlsx
        texts = load_documents_from_xlsx(file_path)
        return [{"content": text, "metadata": {}} for text in texts]
        
    elif file_type == "pptx":
        from app.data_ingest.pptx_ingest import load_documents_from_pptx
        texts = load_documents_from_pptx(file_path)
        return [{"content": text, "metadata": {}} for text in texts]
        
    elif file_type == "html":
        from app.data_ingest.html_ingest import load_documents_from_html
        texts = load_documents_from_html(file_path)
        return [{"content": text, "metadata": {}} for text in texts]
        
    elif file_type == "json":
        from app.data_ingest.json_ingest import load_documents_from_json
        texts = load_documents_from_json(file_path)
        return [{"content": text, "metadata": {}} for text in texts]
        
    elif file_type == "md":
        from app.data_ingest.md_ingest import load_documents_from_md
        texts = load_documents_from_md(file_path)
        return [{"content": text, "metadata": {}} for text in texts]
        
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

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
    
    # Map types to globs
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