# agents/summary_agent.py
# This module implements the SummaryAgent.
# The SummaryAgent is an agent worker specialized in generating context-aware summarizations.
# It reads the user query and the retrieved conversation context from the GraphState,
# executes a summarization request against the LLMService (which triggers DeepSeek-V4-Pro),
# saves the summary results back to the GraphState, and returns an AgentResult log.

import logging

from app.config.settings import settings
from app.models.chat_models import AgentResult
from app.services.llm_service import LLMService
from app.state import GraphState

# Import Langfuse observe decorator if enabled, or fallback to mock NOP decorator.
if settings.langfuse_enabled:
    try:
        from langfuse import observe
    except ImportError:
        def observe(*args, **kwargs):
            def decorator(func):
                return func
            return decorator if args and callable(args[0]) else decorator
else:
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        return decorator if args and callable(args[0]) else decorator

logger = logging.getLogger(__name__)


class SummaryAgent:
    def __init__(self, llm_service: LLMService):
        """
        Injects the LLMService instance.
        """
        self.llm_service = llm_service
        
    @observe(name="summary_agent")
    async def run(self, state: GraphState) -> AgentResult:
        """
        Runs the summary generation task.
        Reads user_message and conversation_context, queries the LLM, updates state, and logs the result.
        """
        logger.info(
            "Summary agent started.",
            extra={
                "route": state.route,
                "message_preview": state.user_message[:120],
                "context_messages": len(state.conversation_context),
            },
        )
        
        # 1. Trigger the summarization request using the LLM Service (routes to DeepSeek model).
        summary = await self.llm_service.summarize(state.user_message, state.conversation_context)
        
        # 2. Record the resulting summary text inside the shared GraphState object.
        state.summary_output = summary
        logger.info(
            "Summary agent completed.",
            extra={"context_messages": len(state.conversation_context)},
        )
        
        # 3. Return the structured AgentResult log.
        return AgentResult(
            agent="summary",
            output=summary,
            metadata={"context_messages": len(state.conversation_context)},
        )
