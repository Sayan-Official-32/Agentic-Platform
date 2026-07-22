# workflows/chat_workflow.py
# This module implements the ChatWorkflow class.
# The Workflow engine acts as the master conductor.
# It coordinates the incoming HTTP request, fetches chat history, checks cache,
# and then delegates the heavy lifting to the compiled LangGraph application.

import asyncio
import logging
import uuid

from app.config.settings import settings
from app.logging_config import clear_log_context, set_log_context, update_log_context
from app.memory.redis_memory import RedisMemoryService
from app.models.chat_models import AgentResult, ChatRequest, ChatResponse
from app.services.conversation_service import ConversationService
from app.state.graph_state import GraphState
from app.workflows.langgraph_workflow import app as langgraph_app

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


class ChatWorkflow:
    def __init__(self) -> None:
        """
        Initializes and links all dependencies for memory and caching.
        The actual LLM/Search services and Agents are now managed by LangGraph.
        """
        self.memory_service = RedisMemoryService(settings.redis_url, settings.redis_ttl_seconds)
        self.cache_service = RedisMemoryService(settings.redis_url, settings.redis_ttl_seconds)
        self.conversation_service = ConversationService()
        
    @observe(name="chat_workflow")
    async def run(self, request: ChatRequest, user_id: uuid.UUID) -> ChatResponse:
        """
        Runs the conversational multi-agent logic cycle using LangGraph.
        """
        is_new_conversation = request.conversation_id is None
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        set_log_context(thread_id=conversation_id, agent_type="workflow")

        session_row = None
        session_file_ids = request.file_ids

        if is_new_conversation:
            session_row = self.conversation_service.create_conversation(
                user_id=str(user_id),
                conversation_id=conversation_id,
                title=request.message[:60],
                file_ids=request.file_ids,
            )
            session_file_ids = request.file_ids
        else:
            session_row = self.conversation_service.find_session_by_conversation_id(conversation_id)
            if session_row:
                if request.file_ids is not None:
                    self.conversation_service.update_file_ids(session_row["id"], request.file_ids)
                    session_file_ids = request.file_ids
                else:
                    session_file_ids = session_row.get("file_ids")
        
        file_ids_str = ""
        if session_file_ids:
            sorted_file_ids = sorted([str(fid) for fid in session_file_ids])
            file_ids_str = ",".join(sorted_file_ids)
            
        cache_key = f"chat:{user_id}:{conversation_id}:{request.message.strip().lower()}:{file_ids_str}"
        cached_answer = self.cache_service.get_value(cache_key)
        stored_context = self.memory_service.get_messages(conversation_id)
        
        logger.info(
            "Chat workflow started.",
            extra={
                "conversation_id": conversation_id,
                "history_count": len(request.history),
                "message_preview": request.message[:120],
                "user_id": str(user_id)
            },
        )

        if cached_answer:
            logger.info("Cache hit for chat response.", extra={"conversation_id": conversation_id})
            return ChatResponse(
                conversation_id=conversation_id,
                route="cache",
                answer=cached_answer,
                agents_used=["cache"],
                agent_results=[
                    AgentResult(agent="cache", output=cached_answer, metadata={"cache_hit": True})
                ],
                cached=True,
                context_messages=len(stored_context),
            )
            
        conversation_context = [message.model_dump() for message in request.history] or stored_context
        self.memory_service.append_message(conversation_id, "user", request.message)
        
        # 5. Initialize the GraphState object (TypedDict) carrying the workflow data
        # Default file_ids to [] if no files are linked to this session to prevent searching across all user files
        active_file_ids = session_file_ids if session_file_ids is not None else []

        state: GraphState = {
            "conversation_id": conversation_id,
            "user_message": request.message,
            "history": request.history,
            "conversation_context": conversation_context,
            "user_id": user_id,
            "file_ids": active_file_ids,
            "route": "summary",
            "summary_output": "",
            "search_output": "",
            "final_answer": "",
            "search_results": None,
            "retrieved_chunks": [],
            "reranked_chunks": [],
        }
        
        logger.info("Invoking LangGraph application.")
        
        # 6. Execute LangGraph workflow
        try:
            final_state = await langgraph_app.ainvoke(state)
        except Exception as exc:
            logger.exception("LangGraph execution failed.", exc_info=exc)
            final_state = dict(state)
            final_state["final_answer"] = f"Workflow failed unexpectedly: {exc}"
            
        route_taken = final_state.get("route", "unknown")
        final_answer = final_state.get("final_answer", "Error: No answer generated.")
        update_log_context(route=route_taken)
            
        # 8. Save the final answer to the Redis session history and caches
        self.memory_service.append_message(conversation_id, "assistant", final_answer)
        self.cache_service.set_value(cache_key, final_answer)

        # 8b. Persist both messages to Supabase for permanent history
        if session_row:
            session_id = session_row["id"]
            self.conversation_service.save_message(session_id, "user", request.message)
            self.conversation_service.save_message(session_id, "assistant", final_answer)
        
        logger.info(
            "Chat workflow completed.",
            extra={
                "conversation_id": conversation_id,
                "route": route_taken,
                "final_answer_preview": final_answer[:160],
            },
        )
        
        model_used = final_state.get("model_used", "Groq (llama-3.1-8b-instant)")

        # 9. Format response payload
        response = ChatResponse(
            conversation_id=conversation_id,
            route=route_taken,
            answer=final_answer,
            agents_used=["langgraph_router"],
            agent_results=[AgentResult(agent="langgraph", output=final_answer, metadata={"route": route_taken})],
            cached=False,
            context_messages=len(self.memory_service.get_messages(conversation_id)),
            model_used=model_used,
            question=request.message,
            sources=final_state.get("search_output", ""),
        )
        clear_log_context()
        return response