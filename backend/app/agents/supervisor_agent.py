# agents/supervisor_agent.py
# This module implements the SupervisorAgent.
# In multi-agent architectures, a "Supervisor" acts as the router/scheduler.
# Its job is to analyze the user's message and determine the optimal execution path (route):
# - "greeting" -> skip RAG/LLM search, return generic hello.
# - "search" -> user wants to see raw document snippets only.
# - "summary" -> user wants general summary.
# - "parallel" -> user wants grounded answers; search Supabase pgvector first, then feed hits into LLM.
# It can perform routing using either LLM text classification (accurate) or keyword-based parsing (fast fallback).

import logging
from app.config.settings import settings
from app.prompts import LLMPrompts
from app.services.llm_service import LLMService, ModelCapability
from typing import Optional


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

class SupervisorAgent:
    
    def __init__(self, llm_service: Optional[LLMService] = None, use_llm_routing: bool = True):
        """
        Initializes the supervisor.
        
        Args:
            llm_service: Shared LLMService instance (needed if use_llm_routing is True).
            use_llm_routing: If True, uses the LLM to classify user intent. Otherwise, uses keyword parsing.
        """
        self.llm_service = llm_service
        self.use_llm_routing = use_llm_routing and llm_service is not None
        
        if self.use_llm_routing:
            logger.info("Supervisor initialized with LLM-based routing")
        else:
            logger.info("Supervisor initialized with keyword-based routing")
     
    @observe(name="supervisor_decide_route")
    async def decide_route(self, message: str) -> str:
        """
        Analyzes the user's message and returns the name of the resolved route:
        "greeting", "search", "summary", or "parallel".
        """
        if self.use_llm_routing:
            try:
                # 1. Attempt LLM classification
                route = await self._llm_based_routing(message)
                logger.info(
                    "Supervisor selected route (LLM-based).",
                    extra={"route": route, "message_preview": message[:120]},
                )
                return route
            except Exception as e:
                # 2. Fall back to keyword routing if the LLM endpoint fails or goes offline
                logger.warning(
                    f"LLM routing failed, falling back to keyword-based: {e}",
                    extra={"message_preview": message[:120]}
                )
                return self._keyword_based_routing(message)
        else:
            # 3. Default to keyword routing
            route = self._keyword_based_routing(message)
            logger.info(
                "Supervisor selected route (keyword-based).",
                extra={"route": route, "message_preview": message[:120]},
            )
            return route
    
    @observe(name="llm_routing_decision")
    async def _llm_based_routing(self, message: str) -> str:
        """
        Asks the LLM to classify the user's message into one of the routing options.
        """
        # Fetch the system prompt directing classification
        prompt = LLMPrompts.routing_decision(user_message=message)
        
        logger.info(
            "Calling LLM for routing decision",
            extra={"message_preview": message[:100], "prompt_length": len(prompt)}
        )
        
        # Call the LLM. We set max_tokens=20 and temperature=0.0 to force a fast,
        # deterministic, single-word response.
        response = await self.llm_service.generate(
            prompt=prompt,
            capability=ModelCapability.QUESTION_ANSWERING,
            max_tokens=20,  
            temperature=0.0, 
        )
        
        logger.info(
            "LLM routing response received",
            extra={
                "raw_response": response,
                "response_length": len(response),
                "message_preview": message[:100]
            }
        )
        
        # Clean the response string (strip whitespace and convert to lowercase)
        route = response.strip().lower()
        
        # Check if any valid route keyword is contained in the response
        valid_routes = ["greeting", "search", "summary", "parallel"]
        for valid_route in valid_routes:
            if valid_route in route:
                logger.info(
                    f"LLM routing extracted '{valid_route}' from response",
                    extra={"raw_response": response}
                )
                return valid_route
            
        # Default fallback route if LLM response is uninterpretable
        logger.warning(
            f"LLM returned invalid route, defaulting to 'parallel'",
            extra={
                "llm_response": response,
                "cleaned_response": route,
                "message_preview": message[:100]
            }
        )
        return "parallel"
    
    def _keyword_based_routing(self, message: str) -> str:
        """
        Simple keyword heuristic routing.
        Looks for exact greetings or document lists keywords.
        """
        lowered = message.strip().lower()
        
        search_only_keywords = ["show me documents", "list documents", "display documents"]
        greeting_keywords = [
            "hello", "hi", "hey", "bonjour", "good morning", "good afternoon", "good evening",
        ]
        
        # If the input matches a greeting keyword, route to greeting
        if lowered in greeting_keywords:
            route = "greeting"
        # If the input contains a search keyword, route to search
        elif any(keyword in lowered for keyword in search_only_keywords):
            route = "search"
        # Default route for everything else
        else:
            route = "parallel"
            
        logger.info(
            "Supervisor selected route.",
            extra={"route": route, "message_preview": message[:120]},
        )
        
        return route