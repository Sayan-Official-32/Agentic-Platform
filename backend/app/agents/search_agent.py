# agents/search_agent.py
# This module implements the SearchAgent.
# In a multi-agent system, an "Agent" is a specialized component focused on a single responsibility.
# The SearchAgent takes the user query from the shared GraphState, executes a query against
# Elasticsearch via the SearchService, formats the matching document details into a readable list,
# updates the GraphState, and returns an AgentResult object.

import logging

from app.config.settings import settings
from app.models.chat_models import AgentResult
from app.services.search_service import SearchService
from app.state import GraphState

# Configure optional Langfuse tracing for this agent
if settings.langfuse_enabled:
    try:
        from langfuse import observe
    except ImportError:
        def observe(*args,**kwargs):
            def decorator(func):
                return func
            return decorator if args and callable(args[0]) else decorator
else:
      def observe(*args, **kwargs):
        def decorator(func):
            return func
        return decorator if args and callable(args[0]) else decorator
    
logger  = logging.getLogger(__name__)

class SearchAgent:
    def __init__(self, search_service: SearchService):
        """
        Injects the Elasticsearch SearchService instance.
        """
        self.search_service = search_service
        
    @observe(name="search_agent")
    async def run(self, state: GraphState) -> AgentResult:
        """
        Executes the search task.
        Reads state.user_message, queries Elasticsearch, sets state.search_results/search_output,
        and returns the AgentResult.
        """
        logger.info(
            "Search agent started.",
            extra={"route": state.route, "message_preview": state.user_message[:120]},
        )
        
        # 1. Query Elasticsearch using the search service
        results = await self.search_service.search(state.user_message)

        # 2. Save raw hits list into the shared state object
        state.search_results = results
        
        # 3. Format the hits list into a beginner-friendly readable text block
        lines = []
        for index, item in enumerate(results):
            location_parts = []
            if item.file_name:
                location_parts.append(item.file_name)
            if item.page_number is not None:
                location_parts.append(f"Page {item.page_number}")

            location = f" ({', '.join(location_parts)})" if location_parts else ""
            lines.append(
                f"{index + 1}. {item.title}{location} — {item.snippet}"
            )

        output = "Search results from Elasticsearch:\n" + "\n".join(lines) if lines else "No matching documents found."
        
        # 4. Save the formatted text block to the state
        state.search_output = output
        logger.info(
            "Search agent completed.",
            extra={"results_count": len(results), "index_name": self.search_service.index_name},
        )
        
        # 5. Return the structured AgentResult log
        return AgentResult(
            agent="search",
            output=output,
            metadata={
                "results_count": len(results),
                "index_name" : self.search_service.index_name
            }
        )
 