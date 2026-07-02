# data_ingest/json_ingest.py
# Parses structured JSON (.json) documents.

import json
import logging
from typing import List, Any

logger = logging.getLogger(__name__)

def _format_node(val: Any) -> str:
    """Formats cell/node value recursively."""
    if isinstance(val, dict):
        return ", ".join(f"{k}: {_format_node(v)}" for k, v in val.items())
    elif isinstance(val, list):
        return "; ".join(_format_node(item) for item in val)
    return str(val)

def load_documents_from_json(file_path: str) -> List[str]:
    """
    Extracts text units from a JSON file.
    If the top-level is a list, each element is serialized as a text item.
    If it is a dict, keys/nesting are serialized.
    """
    text_blocks = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if isinstance(data, list):
            for i, item in enumerate(data):
                text_blocks.append(f"Record {i+1}: {_format_node(item)}")
        elif isinstance(data, dict):
            for key, val in data.items():
                text_blocks.append(f"{key}: {_format_node(val)}")
        else:
            text_blocks.append(str(data))
            
        logger.info(f"Extracted {len(text_blocks)} blocks from JSON: {file_path}")
        return text_blocks
    except Exception as exc:
        logger.error(f"Error parsing JSON file {file_path}: {exc}")
        raise
