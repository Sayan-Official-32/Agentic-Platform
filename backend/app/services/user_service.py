# services/user_service.py
# This service implements user registration, login authentication, and queries
# directly against the Supabase PostgreSQL 'users' table.

import logging
from typing import Optional
from uuid import UUID
from app.services.supabase_service import SupabaseService
from app.models.auth_models import LoginRequest, RegisterRequest, UserResponse
from app.utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        self.supabase = SupabaseService.get_client()

    def register_user(self, request: RegisterRequest) -> UserResponse:
        """
        Registers a new user in the Supabase PostgreSQL database.
        """
        email = request.email.lower().strip()
        logger.info("Registering user in Supabase...", extra={"email": email})
        
        # Check if user already exists
        existing = self.supabase.table("users").select("*").eq("email", email).execute()
        if existing.data:
            logger.warning("Registration failed: User already exists.", extra={"email": email})
            raise ValueError("User Already Exists.")

        # Hash password and insert user
        hashed = hash_password(request.password)
        new_user_data = {
            "email": email,
            "hashed_password": hashed
        }
        
        result = self.supabase.table("users").insert(new_user_data).execute()
        
        if not result.data:
            logger.error("Failed to insert user into database.")
            raise RuntimeError("Database error during registration.")

        user_row = result.data[0]
        logger.info("User registered successfully.", extra={"email": email, "id": user_row["id"]})
        
        return UserResponse(
            id=UUID(user_row["id"]),
            email=user_row["email"],
            full_name=user_row.get("full_name")
        )

    def authenticate_user(self, request: LoginRequest) -> Optional[UserResponse]:
        """
        Verifies login credentials against the database.
        """
        email = request.email.lower().strip()
        logger.info("Authenticating user...", extra={"email": email})
        
        result = self.supabase.table("users").select("*").eq("email", email).execute()
        if not result.data:
            logger.warning("Authentication failed: User not found.", extra={"email": email})
            return None

        user_row = result.data[0]
        if not verify_password(request.password, user_row["hashed_password"]):
            logger.warning("Authentication failed: Incorrect password.", extra={"email": email})
            return None

        logger.info("Authentication successful.", extra={"email": email})
        return UserResponse(
            id=UUID(user_row["id"]),
            email=user_row["email"],
            full_name=user_row.get("full_name")
        )

    def get_user(self, email: str) -> Optional[UserResponse]:
        """
        Retrieves a user profile by email.
        """
        email = email.lower().strip()
        result = self.supabase.table("users").select("*").eq("email", email).execute()
        if not result.data:
            return None
        
        user_row = result.data[0]
        return UserResponse(
            id=UUID(user_row["id"]),
            email=user_row["email"],
            full_name=user_row.get("full_name")
        )
