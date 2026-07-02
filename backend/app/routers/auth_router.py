# routers/auth_router.py
# This module implements the authentication API endpoints (routes) for our backend application.
# It registers /register and /login endpoints under the /api/v1/auth prefix.
# FastAPI uses standard Python type hints in function arguments to validate incoming JSON structures.

import logging

from fastapi import APIRouter, HTTPException, status

from app.config.settings import settings
from app.memory.redis_memory import RedisMemoryService
from app.models.auth_models import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService
from app.services.token_service import TokenService

# APIRouter allows us to split our endpoints across multiple modular files.
# prefix=settings.api_prefix + "/auth" groups all endpoints in this file under /api/v1/auth.
# tags=["auth"] is used by FastAPI to group these routes together in the auto-generated Swagger documentation (/docs).
router = APIRouter(prefix=settings.api_prefix + "/auth", tags=["auth"])
logger = logging.getLogger(__name__)

# Initialize services needed to store accounts and sign JWT keys.
memory_service = RedisMemoryService(settings.redis_url, settings.redis_ttl_seconds)
auth_service = AuthService(memory_service)
token_service = TokenService()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest) -> UserResponse:
    """
    Registers a new user account.
    - response_model=UserResponse: FastAPI ensures the returned object matches the UserResponse schema (hiding passwords).
    - status_code=201 Created: The standard HTTP success code for resource creation.
    """
    logger.info("Register request received.", extra={"user_id": request.email})
    try:
        # Register user via AuthService
        user = auth_service.register_user(request)
        logger.info("Register request completed.", extra={"user_id": request.email})
        return user
    except ValueError as exc:
        # AuthService raises ValueError if the user email is already registered.
        # We catch it and throw a standard FastAPI HTTPException, returning a clean 400 Bad Request error to the client.
        logger.warning("Register request failed.", extra={"user_id": request.email, "reason": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    
    
@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest) -> TokenResponse:
    """
    Logs in an existing user and returns a signed JWT security token.
    """
    logger.info("Login request received.", extra={"user_id": request.email})
    # 1. Verify credentials via AuthService
    user = auth_service.authenticate_user(request)
    if not user:
        logger.warning("Login request rejected.", extra={"user_id": request.email})
        # If authentication fails, raise a standard HTTP 401 Unauthorized error
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # 2. Issue a JWT access token for the authenticated user
    token = token_service.create_access_token(user.email)
    logger.info("Login request completed.", extra={"user_id": user.email})
    # 3. Return the token and user email in a TokenResponse structure
    return TokenResponse(access_token=token, email=user.email)
