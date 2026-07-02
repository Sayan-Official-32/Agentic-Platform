# services/auth_service.py
# This module implements the AuthService class.
# It acts as a controller for user accounts, coordinating registration (signing up),
# authentication (logging in), and profile queries.
# Instead of a heavy relational database (like PostgreSQL), it leverages the RedisMemoryService
# as a mock persistent database, saving user records as JSON strings with permanent TTLs.

import json
from typing import Optional

from app.memory.redis_memory import RedisMemoryService
from app.models.auth_models import LoginRequest, RegisterRequest, UserResponse
from app.utils.security import hash_password, verify_password

class AuthService:
    def __init__(self, memory_service: RedisMemoryService):
        """
        Injects the shared RedisMemoryService instance so this service can write/read user records.
        """
        self.memory_service = memory_service
        
    def register_user(self, request: RegisterRequest) -> UserResponse:
        """
        Registers a new user inside the Redis key-value store.
        
        Raises:
            ValueError: If a user with the same email already exists.
        """
        # 1. Generate the unique Redis key for this user's email, e.g. "user:test@example.com"
        key = self.memory_service.user_key(request.email)
        # 2. Check if this key already exists in Redis/memory
        existing = self.memory_service.get_value(key)
        
        if existing:
            raise ValueError("User Already Exists.")    
        
        # 3. Create the user dictionary, hashing the clear-text password for safety
        payload = {
            "email": request.email,
            "hashed_password": hash_password(request.password)
        }
        
        # 4. Save the user record permanently (ttl=-1 ensures it does not expire)
        self.memory_service.set_value(key, json.dumps(payload), ttl=-1)
        # 5. Return the UserResponse schema, which only exposes the user's email address
        return UserResponse(email=request.email)
    
    def authenticate_user(self, request: LoginRequest) -> Optional[UserResponse]:
        """
        Verifies login credentials.
        Returns a UserResponse if successful, or None if the email is unregistered or the password is incorrect.
        """
        # 1. Fetch user data by email key
        key = self.memory_service.user_key(request.email)
        stored_user = self.memory_service.get_value(key)
        if not stored_user:
            return None

        # 2. Deserialize the user profile
        payload = json.loads(stored_user)
        # 3. Verify the plain-text password against the stored password hash
        if not verify_password(request.password, payload["hashed_password"]):
            return None
        return UserResponse(email=request.email)
    
    def get_user(self, email: str) -> Optional[UserResponse]:
        """
        Fetches an existing user profile by email (used by current-user auth dependencies).
        """
        key = self.memory_service.user_key(email)
        stored_user = self.memory_service.get_value(key)
        if not stored_user:
            return None
        payload = json.loads(stored_user)
        return UserResponse(email=payload["email"])
