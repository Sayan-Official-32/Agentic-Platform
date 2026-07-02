# routers/chat_router.py
# This module implements endpoints relating to chat actions and chat session storage.
# It defines three endpoints:
# 1. POST /chat: Run the multi-agent chat flow (secured by JWT auth).
# 2. GET /conversations/{conversation_id}/context: Fetch historical messages for a chat UUID.
# 3. DELETE /conversations/{conversation_id}/context: Flush memory of a chat UUID.

import logging

from fastapi import APIRouter, Depends

from app.config.settings import settings
from app.dependencies.auth_dependencies import get_current_user
from app.memory.redis_memory import RedisMemoryService
from app.models.auth_models import UserResponse
from app.models.chat_models import ChatRequest, ChatResponse, ConversationContextResponse
from app.workflows.chat_workflow import ChatWorkflow

# Registers endpoints under the base prefix defined in settings (e.g., /api/v1)
router = APIRouter(prefix=settings.api_prefix, tags=["chat"])
logger = logging.getLogger(__name__)

# Instantiate global service/workflow controllers
workflow = ChatWorkflow()
memory_service = RedisMemoryService(settings.redis_url, settings.redis_ttl_seconds)

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: UserResponse = Depends(get_current_user)) -> ChatResponse:
    """
    Submits a user query to the multi-agent orchestration workflow.
    - Depends(get_current_user) runs our security verification function.
      If validation fails, FastAPI raises 401 and this route function is NOT executed.
    - 'async def' tells FastAPI this function executes asynchronously (using non-blocking I/O).
    """
    logger.info(
        "Chat API request received.",
        extra={
            "user_id": str(current_user.id),
            "conversation_id": request.conversation_id or "new",
            "message_preview": request.message[:120],
        },
    )
    # Trigger and await the asynchronous agent workflow run, scoped by user ID
    return await workflow.run(request, current_user.id)


@router.get("/conversations/{conversation_id}/context", response_model=ConversationContextResponse)
def get_conversation_context(
    conversation_id: str,
    current_user: UserResponse = Depends(get_current_user),
) -> ConversationContextResponse:
    """
    Retrieves the chat history messages stored in Redis for a specific conversation ID.
    The {conversation_id} in the path decorator is automatically bound to the 'conversation_id' argument.
    """
    logger.info(
        "Conversation context requested.",
        extra={"user_id": current_user.email, "conversation_id": conversation_id},
    )
    # Fetch from Redis/in-memory list
    messages = memory_service.get_messages(conversation_id)
    return ConversationContextResponse(
        conversation_id=conversation_id,
        message_count=len(messages),
        messages=messages,
    )
    
@router.delete("/conversations/{conversation_id}/context", response_model=ConversationContextResponse)
def clear_conversation_context(
    conversation_id: str,
    current_user: UserResponse = Depends(get_current_user),
) -> ConversationContextResponse:
    """
    Clears all stored chat messages for a specific conversation ID from the database.
    """
    logger.info(
        "Conversation context cleared.",
        extra={"user_id": current_user.email, "conversation_id": conversation_id},
    )
    # Trigger delete operation
    memory_service.clear_messages(conversation_id)
    return ConversationContextResponse(
        conversation_id=conversation_id,
        message_count=0,
        messages=[],
    )


