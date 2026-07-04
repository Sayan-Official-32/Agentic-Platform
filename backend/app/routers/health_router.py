# routers/health_router.py
# This module implements the /health endpoint.
# Health check endpoints are used by monitoring systems (like Kubernetes, AWS target groups,
# or status pingers) to check if the server is up and verify connections to external services
# like Redis and Supabase are healthy.

from fastapi import APIRouter

from app.config.settings import settings
from app.memory.redis_memory import RedisMemoryService
from app.services.search_service import SearchService
from app.services.llm_service import LLMService

# APIRouter is tagged with "health" to categorize it in the openapi docs.
router = APIRouter(tags=["health"])

# Initialize services to verify connection health
memory_service =  RedisMemoryService(settings.redis_url, settings.redis_ttl_seconds)
search_service = SearchService()

@router.get("/health")
def health() -> dict[str, object]:
    """
    Returns the application status, environment, and backend database connectivity indicators.
    """
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "llm_provider": settings.llm_provider,
        "redis_connected": memory_service.using_redis,           # True if connected to Redis
        "supabase_connected": search_service.available,     # True if connected to Supabase
        "token_usage": {
            "prompt_tokens": LLMService._total_prompt_tokens,
            "completion_tokens": LLMService._total_completion_tokens,
            "total_tokens": LLMService._total_tokens,
        }
    }