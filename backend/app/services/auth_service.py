# services/auth_service.py
# This module implements the AuthService class.
# It delegates user actions to the new UserService for Supabase PostgreSQL compatibility.

import logging
from typing import Optional
from app.services.user_service import UserService
from app.models.auth_models import LoginRequest, RegisterRequest, UserResponse

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, memory_service = None):
        """
        Maintains initialization signature compatibility, but routes operations to UserService.
        """
        self.user_service = UserService()
        
    def register_user(self, request: RegisterRequest) -> UserResponse:
        """
        Delegates registration to UserService.
        """
        return self.user_service.register_user(request)
    
    def authenticate_user(self, request: LoginRequest) -> Optional[UserResponse]:
        """
        Delegates authentication to UserService.
        """
        return self.user_service.authenticate_user(request)
    
    def get_user(self, email: str) -> Optional[UserResponse]:
        """
        Delegates user retrieval to UserService.
        """
        return self.user_service.get_user(email)

