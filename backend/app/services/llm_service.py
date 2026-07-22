# services/llm_service.py
# This module implements the LLMService class.
# It acts as the gateway to our Large Language Models (LLMs).
# We connect to the HuggingFace Router using an OpenAI-compatible client API,
# which allows us to route queries dynamically to four different specialized open-source models:
# 1. DeepSeek-V4-Pro (for complex reasoning, thinking, and summarization)
# 2. Qwen2.5-Coder (for generating programming code)
# 3. Llama-3.2-3B (for ultra-fast Q&A and greeting routes)
# 4. Llama-3.1-8B (general purpose fallback and standard Q&A)

import logging
from typing import Dict, List, Optional
from enum import Enum
from openai import OpenAI
from app.prompts import LLMPrompts
from app.config.settings import settings

# If Langfuse tracing is enabled in settings, import the 'observe' decorator to auto-log latency/tokens.
# Otherwise, create a mock observe decorator that does nothing (NOP decorator),
# which prevents import errors and code crashes when Langfuse is disabled.
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

class ModelCapability(Enum):
    """
    Unique capabilities used to route tasks to different LLMs.
    """
    SUMMARIZATION = "summarization"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    QUESTION_ANSWERING = "question_answering"
    
    
class ModelConfig:
    """
    Configuration parameters for the four specialized HuggingFace Router models.
    """
    
    MODELS = {
        "deepseek-ai/DeepSeek-V4-Pro":{
            "capabilities": [ModelCapability.REASONING, ModelCapability.SUMMARIZATION],
            "max_tokens": 4096,
            "temperature": 0.7,
            "best_for": "Complex reasoning, analysis, and summarization",
            "size": "862B"
        },
        
        "Qwen/Qwen2.5-Coder-7B-Instruct": {
            "capabilities": [ModelCapability.CODE_GENERATION],
            "max_tokens": 8192,
            "temperature": 0.2, # Low temperature ensures code is deterministic and syntactically correct
            "best_for": "Code generation and programming tasks",
            "size": "8B"
        },
        
         "meta-llama/Llama-3.2-3B-Instruct": {
            "capabilities": [ModelCapability.QUESTION_ANSWERING],
            "max_tokens": 2048,
            "temperature": 0.7,
            "best_for": "Fast Q&A and simple tasks",
            "size": "3B"
        },
         
        "meta-llama/Llama-3.1-8B-Instruct": {
            "capabilities": [ModelCapability.SUMMARIZATION, ModelCapability.QUESTION_ANSWERING],
            "max_tokens": 4096,
            "temperature": 0.7,
            "best_for": "General purpose tasks and Q&A",
            "size": "8B"
        },
    }
    
class LLMService:
    """
    LLM Service with automatic multi-provider failover.
    Attempts generation through Groq, OpenRouter, and HuggingFace sequentially.
    """
    _total_prompt_tokens = 0
    _total_completion_tokens = 0
    _total_tokens = 0
    
    def __init__(self):
        self.last_used_model: str = "Unknown Model"
        self.langfuse_enabled = settings.langfuse_enabled
        self.providers = []
        self._initialize_providers()
        
    def _initialize_providers(self):
        """Initializes client connections for all available LLM providers in order of priority."""
        # 1. Groq (Ultra-fast priority)
        if settings.groq_api_key:
            try:
                self.providers.append({
                    "name": "Groq",
                    "client": OpenAI(base_url="https://api.groq.com/openai/v1", api_key=settings.groq_api_key),
                    "model": "llama-3.1-8b-instant"
                })
                logger.info("Initialized Groq provider client.")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq provider: {e}")

        # 2. OpenRouter (Secondary fallback)
        if settings.openrouter_api_key:
            try:
                self.providers.append({
                    "name": "OpenRouter",
                    "client": OpenAI(base_url="https://openrouter.ai/api/v1", api_key=settings.openrouter_api_key),
                    "model": "meta-llama/llama-3.1-8b-instruct:free"
                })
                logger.info("Initialized OpenRouter provider client.")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenRouter provider: {e}")

        # 3. HuggingFace (Tertiary fallback)
        if settings.huggingface_api_key:
            try:
                self.providers.append({
                    "name": "HuggingFace",
                    "client": OpenAI(base_url="https://router.huggingface.co/v1", api_key=settings.huggingface_api_key),
                    "model": "Qwen/Qwen2.5-7B-Instruct"
                })
                logger.info("Initialized HuggingFace provider client.")
            except Exception as e:
                logger.warning(f"Failed to initialize HuggingFace provider: {e}")

        if not self.providers:
            logger.warning("No LLM providers configured! Please check API keys in .env.")
            
    def get_model_for_capability(self, capability: ModelCapability) -> str:
        """Picks the best model for a requested capability."""
        capability_models = {
            ModelCapability.SUMMARIZATION: settings.model_summarization,
            ModelCapability.CODE_GENERATION: settings.model_code_generation,
            ModelCapability.QUESTION_ANSWERING: settings.model_question_answering,
            ModelCapability.REASONING: settings.model_reasoning,
        }
        return capability_models.get(capability) or "llama-3.1-8b-instant"
    
    @observe(name="llm_generate")
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.5,
        capability: Optional[ModelCapability] = None,
    ) -> str:
        """
        Sends a request to the LLM with automatic provider failover.
        Cycles through Groq -> OpenRouter -> HuggingFace until one succeeds.
        """
        if not self.providers:
            raise RuntimeError("No LLM provider clients initialized. Check API keys in .env.")
            
        last_exception = None

        for provider in self.providers:
            p_name = provider["name"]
            client = provider["client"]
            target_model = model or provider["model"]
            
            logger.info(
                f"Attempting generation via provider '{p_name}' using model '{target_model}'...",
                extra={"provider": p_name, "model": target_model}
            )

            try:
                completion = client.chat.completions.create(
                    model=target_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                # Record usage metrics
                try:
                    if hasattr(completion, "usage") and completion.usage:
                        LLMService._total_prompt_tokens += getattr(completion.usage, "prompt_tokens", 0)
                        LLMService._total_completion_tokens += getattr(completion.usage, "completion_tokens", 0)
                        LLMService._total_tokens += getattr(completion.usage, "total_tokens", 0)
                except Exception:
                    pass

                response = completion.choices[0].message.content or ""
                self.last_used_model = f"{p_name} ({target_model})"
                logger.info(f"Generation successful via {self.last_used_model}")
                return response

            except Exception as exc:
                logger.warning(f"Provider '{p_name}' failed: {exc}. Attempting next provider...")
                last_exception = exc

        raise RuntimeError(f"All configured LLM providers failed. Last error: {last_exception}")
        
    async def summarize(self, text: str, context: str = "") -> str:
        """Summarizes text using DeepSeek-V4-Pro (highly capable reasoning model)."""
        prompt = LLMPrompts.summarization(text=text, context=context)
        
        return await self.generate(
            prompt=prompt,
            capability=ModelCapability.SUMMARIZATION,
            max_tokens=1024,
            temperature=0.5,
        )
        
    async def generate_code(self, description: str, language: str = "python") -> str:
        """Generates code using Qwen2.5-Coder (specifically trained on codebases)."""
        prompt = LLMPrompts.code_generation(description=description, language=language)
        
        return await self.generate(
            prompt=prompt,
            capability=ModelCapability.CODE_GENERATION,
            max_tokens=2048,
            temperature=0.2,
        )

    async def answer_question(self, question: str, context: str = "") -> str:
        """Fast Q&A queries using Llama-3.2-3B (compact and speedy)."""
        prompt = LLMPrompts.question_answering(question=question, context=context)
        
        return await self.generate(
            prompt=prompt,
            capability=ModelCapability.QUESTION_ANSWERING,
            max_tokens=1024,
            temperature=0.5,
        )

    async def grounded_answer(
        self,
        question: str,
        retrieved_documents: str,
        conversation_history: str = "",
    ) -> str:
        """
        RAG Grounding: Answers user queries using retrieved document snippets as context.
        Instructs the model to limit answers strictly to the provided document facts.
        """
        prompt = LLMPrompts.grounded_answer(
            user_message=question,
            retrieved_documents=retrieved_documents,
            conversation_history=conversation_history,
        )

        return await self.generate(
            prompt=prompt,
            capability=ModelCapability.QUESTION_ANSWERING,
            max_tokens=1024,
            temperature=0.2, # Low temperature reduces hallucination risks
        )

    async def reason(self, problem: str) -> str:
        """Performs complex step-by-step reasoning on logic problems using DeepSeek-V4-Pro."""
        prompt = LLMPrompts.reasoning(problem=problem)
        
        return await self.generate(
            prompt=prompt,
            capability=ModelCapability.REASONING,
            max_tokens=2048,
            temperature=0.5,
        )

    def list_available_models(self) -> List[Dict]:
        """Utility listing available models, their sizes, and what they are optimized for."""
        return [
            {
                "name": name,
                "capabilities": [cap.value for cap in config["capabilities"]],
                "best_for": config["best_for"],
                "size": config["size"],
                "max_tokens": config["max_tokens"],
            }
            for name, config in ModelConfig.MODELS.items()
        ]