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
    LLM Service using HuggingFace Router with OpenAI-compatible API.
    Selects specialized models dynamically depending on task requirements.
    """
    
    def __init__(self):
        self.client = None
        self.langfuse_enabled = settings.langfuse_enabled
        self._initialize_client()
        
    def _initialize_client(self):
        """Initializes the OpenAI API client configured to hit HuggingFace's API gateway endpoint."""
        if not settings.huggingface_api_key:
            logger.warning("HuggingFace API key not configured")
            return
        
        # HuggingFace provides an OpenAI-compatible endpoint.
        # This allows us to use the official 'OpenAI' SDK, simply swapping out the base_url.
        self.client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=settings.huggingface_api_key,
        )
        
        if self.langfuse_enabled:
            logger.info("HuggingFace Router client initialized with Langfuse tracing enabled")
        else:
            logger.info("HuggingFace Router client initialized (Langfuse disabled)")
            
    def get_model_for_capability(self, capability: ModelCapability) -> str:
        """
        Picks the best model for a requested capability.
        Allows overriding defaults via custom settings from the .env configuration.
        """
        capability_models = {
            ModelCapability.SUMMARIZATION: settings.model_summarization,
            ModelCapability.CODE_GENERATION: settings.model_code_generation,
            ModelCapability.QUESTION_ANSWERING: settings.model_question_answering,
            ModelCapability.REASONING: settings.model_reasoning,
        }
        
        custom_model = capability_models.get(capability)
        if custom_model:
            logger.info(f"Using custom model for {capability.value}: {custom_model}")
            return custom_model
        
        # Fallback default assignments
        default_models = {
            ModelCapability.SUMMARIZATION: "deepseek-ai/DeepSeek-V4-Pro",
            ModelCapability.CODE_GENERATION: "Qwen/Qwen2.5-Coder-7B-Instruct",
            ModelCapability.QUESTION_ANSWERING: "meta-llama/Llama-3.2-3B-Instruct",
            ModelCapability.REASONING: "deepseek-ai/DeepSeek-V4-Pro",
        }
        
        model = default_models.get(capability, "meta-llama/Llama-3.1-8B-Instruct")
        logger.info(f"Using default model for {capability.value}: {model}")
        return model
    
    @observe(name="llm_generate")
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        capability: Optional[ModelCapability] = None,
        ) -> str:
        """
        Sends a request to the LLM and returns the generated string output.
        
        Args:
            prompt: Text prompt/context sent to the model.
            model: Optional name of specific model. If omitted, uses capability to resolve it.
            max_tokens: Limit on response tokens.
            temperature: Creativity control (0.0 is deterministic, 1.0 is highly creative).
            capability: Triggers model routing based on task scope.
        """
        if not self.client:
            raise RuntimeError("HuggingFace Router client not initialized. Check HF_TOKEN.")
        
        # 1. Resolve which model string to use
        if not model and capability:
            model = self.get_model_for_capability(capability)
        elif not model:
            model = "meta-llama/Llama-3.1-8B-Instruct"
            
        logger.info(
            f"Generating with HuggingFace Router",
            extra={"model": model, "temperature": temperature, "max_tokens": max_tokens}
        )
        
        try:
          # 2. Call the chat completion endpoint
          completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature,
          )
          
          # 3. Retrieve response text content
          response = completion.choices[0].message.content or ""
          logger.info(f"Generated {len(response)} characters")
            
          return response
        except Exception as e:
            logger.error(f"Error generating with HuggingFace Router: {e}")
            raise
        
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
            temperature=0.7,
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
            temperature=0.7,
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