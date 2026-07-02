# memory/redis_memory.py
# This module implements the RedisMemoryService.
# Redis is a very fast, in-memory key-value database commonly used for caching and storing short-term session state.
# Here, we use Redis to store conversation message history (so the LLM remembers chat history) and to cache answers.
# If Redis is not running/available, the class automatically falls back to standard python in-memory dictionaries.
# This prevents database outages from breaking local developments.

import json
from typing import Dict, List, Optional

class RedisMemoryService:
    def __init__(self, url: str, ttl_seconds: int):
        """
        Initializes the memory service.
        If the Redis library is installed and a server is reachable, it pings the server to establish a connection client.
        Otherwise, it initializes local python dictionaries as a fallback storage mechanism.
        """
        self.url = url
        # TTL = Time To Live. Indicates how many seconds data should stay in Redis before expiring automatically.
        self.ttl_seconds = ttl_seconds
        self._client = None
        # Fallback local in-memory storage (clears every time the backend server restarts)
        self._memory_store: Dict[str, List[Dict[str, str]]] = {}
        self._kv_store: Dict[str, str] = {}
        
        try:
            # Dynamically import the redis library so the app can start even if the redis driver is not installed.
            import importlib
            
            redis_module = importlib.import_module("redis")
            # Connect to Redis. decode_responses=True returns regular strings instead of binary bytes.
            self._client = redis_module.from_url(url, decode_responses=True)
            # Send a PING command to confirm connection. If unreachable, this throws an exception.
            self._client.ping()
        except Exception:
            # Fall back to local memory if Redis connection fails
            self._client = None    
            
    def conversation_key(self, conversation_id: str) -> str:
        """Returns a namespaced string key to store conversation history, e.g., 'conversation:123:messages'."""
        return f"conversation:{conversation_id}:messages"      
    
    def user_key(self, email: str) -> str:
        """Returns a namespaced string key to store user profiles, e.g., 'user:john@example.com'."""
        return f"user:{email}"
    
    def get_messages(self, conversation_id: str) -> List[Dict[str, str]]:
        """
        Retrieves the list of chat messages for a given conversation.
        """
        if self._client:
            try:
                # lrange (List Range) fetches elements from a Redis List between startIndex (0) and endIndex (-1, representing the end of the list).
                items = self._client.lrange(self.conversation_key(conversation_id), 0, -1)
                # Redis stores raw strings, so we must JSON deserialize each message back into a Python dictionary.
                return [json.loads(item) for item in items]
            except Exception:
                # Fall back to local dict if Redis fails mid-operation
                return self._memory_store.get(conversation_id, [])
        return self._memory_store.get(conversation_id, [])
    
    def append_message(self, conversation_id: str, role: str, content: str) -> None:
        """
        Appends a new chat message to a conversation's history.
        """
        payload = {"role": role, "content": content}
        if self._client:
            try:
                key = self.conversation_key(conversation_id)
                # rpush (Right Push) appends the JSON string message payload to the tail end of the Redis list.
                self._client.rpush(key, json.dumps(payload))
                # reset the expiration timer so the chat history doesn't expire prematurely.
                self._client.expire(key, self.ttl_seconds)
                return
            except Exception:
                pass
        # Fallback dictionary storage
        self._memory_store.setdefault(conversation_id, []).append(payload)
        
    def clear_messages(self, conversation_id: str) -> None:
        """
        Deletes a conversation history from the store.
        """
        if self._client:
            try:
                # delete removes the key entirely from Redis.
                self._client.delete(self.conversation_key(conversation_id))
                return
            except Exception:
                pass
        self._memory_store.pop(conversation_id, None)

    def get_value(self, key: str) -> Optional[str]:
        """
        Fetches a generic string value by its key (used for caching chat answers).
        """
        if self._client:
            try:
                # standard key get
                return self._client.get(key)
            except Exception:
                return self._kv_store.get(key)
        return self._kv_store.get(key)
    
    def set_value(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """
        Set a key-value pair in Redis or in-memory store.
        
        Args:
            key: The key to store
            value: The value to store
            ttl: Time to live in seconds. If None, uses default ttl_seconds.
                 If -1, stores permanently without expiration.
        """
        if self._client:
            try:
                if ttl == -1:
                    # set saves the value with no expiration
                    self._client.set(key, value)
                else:
                    expiry = ttl if ttl is not None else self.ttl_seconds
                    # setex sets the value and assigns an automatic expiration timeout (in seconds)
                    self._client.setex(key, expiry, value)
                return
            except Exception:
                pass
        self._kv_store[key] = value

    @property
    def using_redis(self) -> bool:
        """Helper boolean property indicating whether Redis client connection is active."""
        return self._client is not None