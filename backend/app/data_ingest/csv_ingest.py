# data_ingest/csv_ingest.py
# This module provides a simple parser for loading document snippets from CSV files.
# It reads standard comma-separated values files and formats each row into a dictionary representing a structured document.

import csv
from typing import Dict, List


def load_documents_from_csv(file_path: str) -> List[Dict[str, str]]:
    """
    Reads a CSV file containing columns like 'title', 'snippet', 'category', and 'source',
    and loads each row as a structured dictionary.
    
    Args:
        file_path: The filesystem path to the CSV file.
        
    Returns:
        List[Dict[str, str]]: A list of dictionaries representing the rows of the CSV.
    """
    documents: List[Dict[str, str]] = []
    # Open the file. newline="" is recommended by python's csv module to prevent line-ending translation issues.
    # encoding="utf-8" ensures we support international characters and symbols correctly.
    with open(file_path, newline="", encoding="utf-8") as csv_file:
        # DictReader reads each row as a dictionary where key is header name, value is cell value.
        reader = csv.DictReader(csv_file)
        for row in reader:
            # Map each row field into a document dictionary format.
            documents.append(
                {
                    "title": row["title"],
                    "snippet": row["snippet"],
                    "category": row["category"],
                    "source": row.get("source", "csv-ingest"), # Default to 'csv-ingest' if source is missing
                }
            )
    return documents


