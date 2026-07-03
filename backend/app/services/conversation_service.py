# services/conversation_service.py
# Manages conversation sessions and messages persistence in Supabase.
# Provides CRUD operations for conversations and their messages.

import logging
from typing import List, Optional, Dict, Any
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Service for managing per-user conversation history in Supabase.
    Uses the 'conversation_sessions' table for conversation metadata
    and 'conversation_messages' table for individual messages.
    """

    def list_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all conversations for a given user, ordered by most recently active first.
        """
        try:
            client = SupabaseService.get_client()
            response = (
                client.table("conversation_sessions")
                .select("id, conversation_id, title, file_ids, created_at, last_active_at")
                .eq("user_id", user_id)
                .order("last_active_at", desc=True)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return []

    def create_conversation(
        self, user_id: str, conversation_id: str, title: Optional[str] = None, file_ids: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Creates a new conversation session row in Supabase.
        """
        try:
            client = SupabaseService.get_client()
            response = (
                client.table("conversation_sessions")
                .insert({
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "title": title or "New Chat",
                    "file_ids": file_ids or [],
                })
                .execute()
            )
            if response.data:
                logger.info(f"Created conversation {conversation_id} for user {user_id}")
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            return None

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """
        Deletes a conversation and its messages (cascade) for a given user.
        Uses the internal UUID 'id' from conversation_sessions.
        """
        try:
            client = SupabaseService.get_client()
            # Delete the session row — messages cascade automatically
            client.table("conversation_sessions").delete().eq("id", conversation_id).eq("user_id", user_id).execute()
            logger.info(f"Deleted conversation {conversation_id} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            return False

    def get_conversation_messages(self, session_id: str) -> List[Dict[str, str]]:
        """
        Fetches all messages for a conversation session, ordered by creation time.
        'session_id' is the UUID primary key of conversation_sessions.
        """
        try:
            client = SupabaseService.get_client()
            response = (
                client.table("conversation_messages")
                .select("role, content, created_at")
                .eq("conversation_id", session_id)
                .order("created_at", desc=False)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to get conversation messages: {e}")
            return []

    def save_message(self, session_id: str, role: str, content: str) -> None:
        """
        Saves a message to the conversation_messages table and updates last_active_at.
        'session_id' is the UUID primary key of conversation_sessions.
        """
        try:
            client = SupabaseService.get_client()
            # Insert the message
            client.table("conversation_messages").insert({
                "conversation_id": session_id,
                "role": role,
                "content": content,
            }).execute()
            # Update last_active_at timestamp
            client.table("conversation_sessions").update({
                "last_active_at": "now()",
            }).eq("id", session_id).execute()
        except Exception as e:
            logger.error(f"Failed to save message: {e}")

    def update_title(self, session_id: str, title: str) -> None:
        """
        Updates the title of a conversation session.
        """
        try:
            client = SupabaseService.get_client()
            client.table("conversation_sessions").update({
                "title": title[:60],
            }).eq("id", session_id).execute()
        except Exception as e:
            logger.error(f"Failed to update conversation title: {e}")

    def find_session_by_conversation_id(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Looks up a conversation_sessions row by its text conversation_id field.
        """
        try:
            client = SupabaseService.get_client()
            response = (
                client.table("conversation_sessions")
                .select("id, conversation_id, title, file_ids, created_at, last_active_at")
                .eq("conversation_id", conversation_id)
                .limit(1)
                .execute()
            )
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to find session by conversation_id: {e}")
            return None

    def update_file_ids(self, session_id: str, file_ids: List[str]) -> None:
        """
        Updates the associated file IDs for a conversation session.
        """
        try:
            client = SupabaseService.get_client()
            client.table("conversation_sessions").update({
                "file_ids": file_ids
            }).eq("id", session_id).execute()
        except Exception as e:
            logger.error(f"Failed to update conversation file_ids: {e}")
