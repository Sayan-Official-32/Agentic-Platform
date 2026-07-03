# routers/chat_router.py
# This module implements endpoints relating to chat actions and chat session storage.
# It defines endpoints for:
# 1. POST /chat: Run the multi-agent chat flow (secured by JWT auth).
# 2. GET /conversations: List all conversations for the current user.
# 3. GET /conversations/{conversation_id}/messages: Fetch messages for a conversation.
# 4. DELETE /conversations/{conversation_id}: Delete a conversation and its messages.
# 5. GET /conversations/{conversation_id}/context: Fetch historical messages from Redis.
# 6. DELETE /conversations/{conversation_id}/context: Flush Redis memory.

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.config.settings import settings
from app.dependencies.auth_dependencies import get_current_user
from app.memory.redis_memory import RedisMemoryService
from app.models.auth_models import UserResponse
from app.models.chat_models import ChatRequest, ChatResponse, ConversationContextResponse
from app.services.conversation_service import ConversationService
from app.workflows.chat_workflow import ChatWorkflow

# Registers endpoints under the base prefix defined in settings (e.g., /api/v1)
router = APIRouter(prefix=settings.api_prefix, tags=["chat"])
logger = logging.getLogger(__name__)

# Instantiate global service/workflow controllers
workflow = ChatWorkflow()
memory_service = RedisMemoryService(settings.redis_url, settings.redis_ttl_seconds)
conversation_service = ConversationService()

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


@router.get("/conversations")
def list_conversations(current_user: UserResponse = Depends(get_current_user)) -> list:
    """
    Lists all conversation sessions for the authenticated user, ordered by most recent first.
    """
    return conversation_service.list_conversations(str(current_user.id))


@router.post("/conversations")
def create_empty_conversation(
    request_data: dict,
    current_user: UserResponse = Depends(get_current_user),
) -> dict:
    """
    Explicitly creates a new empty conversation session record.
    """
    import uuid
    conversation_id = request_data.get("conversation_id") or str(uuid.uuid4())
    title = request_data.get("title") or "New Chat"
    file_ids = request_data.get("file_ids") or []
    
    session = conversation_service.create_conversation(
        user_id=str(current_user.id),
        conversation_id=conversation_id,
        title=title,
        file_ids=file_ids,
    )
    if not session:
        raise HTTPException(status_code=500, detail="Failed to create conversation session.")
    return session


@router.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: str,
    current_user: UserResponse = Depends(get_current_user),
) -> dict:
    """
    Retrieves all persisted messages for a specific conversation session.
    conversation_id here is the UUID primary key of the conversation_sessions table.
    """
    messages = conversation_service.get_conversation_messages(conversation_id)
    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "message_count": len(messages),
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    current_user: UserResponse = Depends(get_current_user),
) -> dict:
    """
    Deletes a conversation session and all its messages (cascade).
    conversation_id here is the UUID primary key of the conversation_sessions table.
    """
    success = conversation_service.delete_conversation(conversation_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete conversation.")
    return {"status": "deleted", "conversation_id": conversation_id}


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


