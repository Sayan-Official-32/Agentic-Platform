# config/settings.py
# This module loads environment variables (often from a .env file) and maps them into a strongly-typed Pydantic model.
# By using Pydantic, we guarantee that all configuration settings have the correct data types (e.g. ints, strings, lists)
# and are validated immediately when the backend starts up, avoiding configuration-related errors later.

import os
from typing import List, Literal
from dotenv import load_dotenv
from pydantic import BaseModel

# load_dotenv reads key-value pairs from a .env file and sets them as environment variables.
# override=True ensures that values specified inside the .env file will overwrite existing environment variables.
load_dotenv(override=True)

class Settings(BaseModel):
    """
    Pydantic BaseModel representing our application settings.
    Each attribute has a default value, which is used if the corresponding environment variable is not defined.
    """
    
    # --- General Application Config ---
    app_name: str = os.getenv("APP_NAME", "Multi Agent Starter Backend")
    app_env: str = os.getenv("APP_ENV", "development")
    api_prefix: str = os.getenv("API_PREFIX", "/api/v1")
    
    # BACKEND_CORS_ORIGINS defines which web app URLs are allowed to make API requests to this backend.
    # The split(",") creates a list of allowed origins, e.g. ["http://localhost:3000", "http://127.0.0.1:3000"]
    backend_cors_origins: List[str] = [
        item.strip()
        for item in os.getenv(
            "BACKEND_CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if item.strip()
    ]
    
    # --- LLM Provider Selection ---
    # Literal specifies that llm_provider MUST be either "ollama" or "huggingface". Any other value will raise a validation error.
    llm_provider: Literal["ollama", "huggingface"] = os.getenv("LLM_PROVIDER", "ollama") 
    
    # --- Ollama Configuration (Local LLMs) ---
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    
    # --- HuggingFace API Router Configuration (Cloud LLMs) ---
    huggingface_api_key: str = os.getenv("HUGGINGFACE_API_KEY", "")
    huggingface_model: str = os.getenv("HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
    
    # --- Additional Failover Provider Configurations ---
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    
    # --- Specialized Models for Multi-Agent Workflows ---
    # These settings allow routing specific tasks (code, summarization, etc.) to different LLMs if needed.
    model_summarization: str = os.getenv("MODEL_SUMMARIZATION", "") 
    model_code_generation: str = os.getenv("MODEL_CODE_GENERATION", "")
    model_question_answering: str = os.getenv("MODEL_QUESTION_ANSWERING", "")
    model_reasoning: str = os.getenv("MODEL_REASONING", "")
    
    # --- Redis Memory Configuration ---
    # Redis is used to store chat history (conversation_id -> messages list) and cached responses.
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # redis_ttl_seconds determines how long (in seconds) the conversation history is kept in Redis before it expires (3600s = 1 hour).
    redis_ttl_seconds: int = int(os.getenv("REDIS_TTL_SECONDS", "3600"))
    
    # --- Supabase table setting compatibility ---

    # --- Supabase Configuration ---
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    supabase_storage_bucket: str = os.getenv("SUPABASE_STORAGE_BUCKET", "user-documents")

    # --- Embedding Model Settings ---
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    embedding_dims: int = int(os.getenv("EMBEDDING_DIMS", "384"))
    embedding_cache_ttl: int = int(os.getenv("EMBEDDING_CACHE_TTL", "86400"))

    # --- Text Chunking Settings ---
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    # --- Vector Search Settings ---
    vector_top_k: int = int(os.getenv("VECTOR_TOP_K", "10"))

    # --- Reranker Model Settings ---
    reranker_enabled: bool = os.getenv("RERANKER_ENABLED", "true").lower() == "true"
    reranker_model: str = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    reranker_top_k: int = int(os.getenv("RERANKER_TOP_K", "5"))
    
    # --- Langfuse Configuration (LLM Tracing & Observability) ---
    # Langfuse is used to trace LLM calls, costs, latency, and steps in multi-agent workflows.
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "http://localhost:3001")
    langfuse_public_key: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    langfuse_secret_key: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    langfuse_env: str = os.getenv("LANGFUSE_ENV", "local")
    langfuse_user_id: str = os.getenv("LANGFUSE_USER_ID", "local-dev")
    # Indicates whether Langfuse tracking should be active
    langfuse_enabled: bool = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    
    # --- Authentication (JWT Security Tokens) ---
    auth_secret_key: str = os.getenv("AUTH_SECRET_KEY", "change-me-in-real-projects")
    auth_algorithm: str = os.getenv("AUTH_ALGORITHM", "HS256")
    auth_token_expiry_minutes: int = int(os.getenv("AUTH_TOKEN_EXPIRY_MINUTES", "120"))
    
# Instantiate a single global instance of Settings.
# Importing this settings object in other files gives direct access to all configuration variables.
settings: Settings = Settings()