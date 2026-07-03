# workflows/chat_workflow.py
# This module implements the ChatWorkflow class.
# The Workflow engine acts as the master conductor.
# It coordinates the incoming HTTP request, fetches chat history from Redis, checks the cache,
# calls the Supervisor to select a path, runs the selected agents, processes grounding if needed,
# updates the chat history database, and caches the final answer.

import asyncio
import logging
import uuid
from typing import cast

from app.agents.search_agent import SearchAgent
from app.agents.summary_agent import SummaryAgent
from app.agents.supervisor_agent import SupervisorAgent
from app.config.settings import settings
from app.logging_config import clear_log_context, set_log_context, update_log_context
from app.memory.redis_memory import RedisMemoryService
from app.models.chat_models import AgentResult, ChatRequest, ChatResponse
from app.services.llm_service import LLMService
from app.services.search_service import SearchService
from app.services.conversation_service import ConversationService
from app.state import GraphState

# Configure optional Langfuse tracing for this workflow
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
        Initializes and links all dependencies, services, and agent workers.
        """
        # Memory service stores actual chat histories (session memory)
        self.memory_service = RedisMemoryService(settings.redis_url, settings.redis_ttl_seconds)
        # Cache service caches question -> answer pairs to save LLM costs and respond instantly
        self.cache_service = RedisMemoryService(settings.redis_url, settings.redis_ttl_seconds)
        self.search_service = SearchService()
        self.llm_service = LLMService()
        self.supervisor = SupervisorAgent(llm_service=self.llm_service, use_llm_routing=True)
        self.summary_agent = SummaryAgent(self.llm_service)
        self.search_agent = SearchAgent(self.search_service)
        self.conversation_service = ConversationService()
        
    @observe(name="chat_workflow")
    async def run(self, request: ChatRequest, user_id: uuid.UUID) -> ChatResponse:
        """
        Runs the conversational multi-agent logic cycle.
        """
        # 1. Establish conversation UUID
        is_new_conversation = request.conversation_id is None
        conversation_id = request.conversation_id or str(uuid.uuid4())
        # Set the logger's thread-local context variables for request tracking
        set_log_context(thread_id=conversation_id, agent_type="workflow")

        # 1b. If this is a brand-new conversation, create a session row in Supabase
        session_row = None
        if is_new_conversation:
            session_row = self.conversation_service.create_conversation(
                user_id=str(user_id),
                conversation_id=conversation_id,
                title=request.message[:60],
                file_ids=request.file_ids,
            )
        else:
            session_row = self.conversation_service.find_session_by_conversation_id(conversation_id)
            if session_row and request.file_ids is not None:
                self.conversation_service.update_file_ids(session_row["id"], request.file_ids)
        
        # 2. Check if this exact question has a cached response in Redis (user-scoped and document-aware)
        file_ids_str = ""
        if request.file_ids:
            sorted_file_ids = sorted([str(fid) for fid in request.file_ids])
            file_ids_str = ",".join(sorted_file_ids)
            
        cache_key = f"chat:{user_id}:{conversation_id}:{request.message.strip().lower()}:{file_ids_str}"
        cached_answer = self.cache_service.get_value(cache_key)
        # Fetch previous conversation history list from Redis memory
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

        # 3. Cache Hit Path: If the answer is cached, bypass agent runs and return immediately
        if cached_answer:
            logger.info("Cache hit for chat response.", extra={"conversation_id": conversation_id})
            return ChatResponse(
                conversation_id=conversation_id,
                route="cache",
                answer=cached_answer,
                agents_used=["cache"],
                agent_results=[
                    AgentResult(
                        agent="cache",
                        output=cached_answer,
                        metadata={"cache_hit": True},
                    )
                ],
                cached=True,
                context_messages=len(stored_context),
            )
            
        # 4. Compile the full conversation history. Use incoming request history if supplied;
        # otherwise pull from the Redis stored_context.
        conversation_context = [message.model_dump() for message in request.history] or stored_context
        # Append the new user message to Redis memory database
        self.memory_service.append_message(conversation_id, "user", request.message)
        
        # 5. Initialize the GraphState object carrying the workflow data
        state = GraphState(
            conversation_id=conversation_id,
            user_message=request.message,
            history=request.history,
            conversation_context=conversation_context,
            user_id=user_id,
            file_ids=request.file_ids
        )
        
        # 6. Ask the Supervisor to select the routing path based on the user's message
        state.route = await self.supervisor.decide_route(request.message)
        update_log_context(route=state.route)
        
        logger.info(
            "Workflow route resolved.",
            extra={
                "conversation_id": conversation_id,
                "route": state.route,
                "stored_context_messages": len(stored_context),
            },
        )
        
        agent_results: list[AgentResult] = []

        # 7. Execute the route branches
        # --- Greeting Route ---
        if state.route == "greeting":
            logger.info("Handling greeting route.")
            greeting_reply = (
                "Hello, bonjour — how can I help you?\n\n"
                "You can ask me to summarize a topic, search the indexed knowledge base, "
                "or do both in parallel."
            )
            state.final_answer = greeting_reply
            agent_results.append(
                AgentResult(
                    agent="assistant",
                    output=greeting_reply,
                    metadata={"route": "greeting"},
                )
            )
        # --- Summary Route (LLM only) ---
        elif state.route == "summary":
            logger.info("Handling summary route.")
            try:
                agent_results.append(await self.summary_agent.run(state))
                state.final_answer = state.summary_output
            except Exception as exc:
                logger.exception("Summary route failed; using fallback.")
                fallback = (
                    "Summary agent is temporarily unavailable because the configured LLM endpoint "
                    f"could not be reached. Error: {exc}"
                )
                state.summary_output = fallback
                state.final_answer = fallback
                agent_results.append(
                    AgentResult(
                        agent="summary",
                        output=fallback,
                        metadata={"fallback": True, "reason": "llm_unavailable"},
                    )
                )
        # --- Search Route (Supabase only) ---
        elif state.route == "search":
            logger.info("Handling search route.")
            agent_results.append(await self.search_agent.run(state))
            state.final_answer = state.search_output
        # --- Parallel / RAG Route (Search + Summary + Grounded Answer compilation) ---
        else:
            logger.info("Handling parallel route.")
            
            # A. Execute the Search Agent branch
            try:
                search_agent_result = await self.search_agent.run(state)
                agent_results.append(search_agent_result)
            except Exception as exc:
                logger.exception("Parallel search branch failed.", exc_info=exc)
                search_fallback = AgentResult(
                    agent="search",
                    output=f"Search agent failed unexpectedly. Error: {exc}",
                    metadata={"fallback": True, "reason": "search_failed"},
                )
                state.search_output = search_fallback.output
                agent_results.append(search_fallback)

            # B. Execute the Summary Agent branch
            try:
                summary_agent_result = await self.summary_agent.run(state)
                agent_results.append(summary_agent_result)
            except Exception as exc:
                logger.exception("Parallel summary branch failed.", exc_info=exc)
                summary_fallback = AgentResult(
                    agent="summary",
                    output=(
                        "Summary agent is temporarily unavailable because the configured LLM endpoint "
                        f"could not be reached. Error: {exc}"
                    ),
                    metadata={"fallback": True, "reason": "llm_unavailable"},
                )
                state.summary_output = summary_fallback.output
                agent_results.append(summary_fallback)

            # C. Grounded Answer Synthesis
            # If Supabase/pgvector hits were successfully found, pass them along with the draft summary
            # and chat history to the LLM to generate a factual, grounded response.
            if state.search_results:
                # Format conversation history list as flat text lines
                conversation_history = "\n".join(
                    f"{message.get('role', 'unknown')}: {message.get('content', '')}"
                    for message in conversation_context
                )
                # Compile source files list
                source_lines = []
                for item in state.search_results:
                    source_line = f"- {item.title}"
                    if item.page_number is not None:
                        source_line += f", page {item.page_number}"
                    if item.file_name:
                        source_line += f" ({item.file_name})"
                    source_lines.append(source_line)

                grounded_context = (
                    f"{state.search_output}\n\n"
                    f"Draft summary:\n{state.summary_output}\n\n"
                    f"Sources:\n" + "\n".join(source_lines)
                )

                try:
                    # Run RAG Grounding LLM request
                    grounded_answer = await self.llm_service.grounded_answer(
                        question=request.message,
                        retrieved_documents=grounded_context,
                        conversation_history=conversation_history,
                    )
                    top_result = state.search_results[0]
                    source_line = f"Source: {top_result.title}" + (
                        f", page {top_result.page_number}"
                        if top_result.page_number is not None
                        else ""
                    )
                    state.final_answer = (
                        f"{grounded_answer.strip()}\n"
                        f"{source_line}"
                    )
                    agent_results.append(
                        AgentResult(
                            agent="answer",
                            output=state.final_answer,
                            metadata={"grounded": True},
                        )
                    )
                except Exception as exc:
                    # Fall back to raw summary + top source details if grounding fails
                    logger.exception("Grounded answer generation failed.", exc_info=exc)
                    top_result = state.search_results[0]
                    source_line = f"Source: {top_result.title}" + (
                        f", page {top_result.page_number}"
                        if top_result.page_number is not None
                        else ""
                    )
                    state.final_answer = (
                        f"{state.summary_output.strip()}\n"
                        f"{source_line}"
                    )
            else:
                # If no matching search hits were found, default directly to the summary output
                state.final_answer = state.summary_output
            
        # 8. Save the final answer to the Redis session history and caches
        self.memory_service.append_message(conversation_id, "assistant", state.final_answer)
        self.cache_service.set_value(cache_key, state.final_answer)

        # 8b. Persist both messages to Supabase for permanent history
        if session_row:
            session_id = session_row["id"]
            self.conversation_service.save_message(session_id, "user", request.message)
            self.conversation_service.save_message(session_id, "assistant", state.final_answer)
        
        logger.info(
            "Chat workflow completed.",
            extra={
                "conversation_id": conversation_id,
                "route": state.route,
                "agents_used": [result.agent for result in agent_results],
                "final_answer_preview": state.final_answer[:160],
            },
        )
        
        # 9. Format response payload
        response = ChatResponse(
            conversation_id=conversation_id,
            route=state.route,
            answer=state.final_answer,
            agents_used=[result.agent for result in agent_results],
            agent_results=agent_results,
            cached=False,
            context_messages=len(self.memory_service.get_messages(conversation_id)),
        )
        # Clear request tracking variables from logger thread context
        clear_log_context()
        return response