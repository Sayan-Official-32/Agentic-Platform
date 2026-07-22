# tools/rag_tools.py
# This module defines LangChain tools that wrap existing backend services.
# These tools can be invoked by LangChain Agents or LangGraph nodes.

import logging
from typing import List, Optional
from langchain_core.tools import tool

from app.services.search_service import SearchService
from app.services.llm_service import LLMService
from app.prompts import LLMPrompts

logger = logging.getLogger(__name__)

search_service = SearchService()
llm_service = LLMService()

@tool
async def pgvector_search(query: str, user_id: str, file_ids: Optional[List[str]] = None) -> str:
    """
    Searches the Supabase pgvector database for documents relevant to the query.
    Returns a formatted string of search results with titles and snippets.
    """
    logger.info(f"Tool executed: pgvector_search for query '{query}'")
    try:
        results = await search_service.search(query, user_id, file_ids=file_ids)
        if not results:
            return "No matching documents found."
        
        output = "Search results from pgvector:\n"
        for i, item in enumerate(results, 1):
            title = item.title or "Unknown Document"
            page = f" (Page {item.page_number})" if item.page_number else ""
            output += f"{i}. {title}{page} — {item.snippet}\n\n"
        return output
    except Exception as exc:
        logger.error(f"Search tool failed: {exc}")
        return f"Search failed: {exc}"

@tool
async def generate_summary(prompt: str) -> str:
    """
    Calls the LLM to generate a summary or answer based solely on its internal knowledge, 
    without any database retrieval.
    """
    logger.info("Tool executed: generate_summary")
    try:
        system_prompt = LLMPrompts.summary_generation(user_message=prompt)
        response = await llm_service.generate(system_prompt)
        return response
    except Exception as exc:
        logger.error(f"Summary tool failed: {exc}")
        return f"Summary generation failed: {exc}"
