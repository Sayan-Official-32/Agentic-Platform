# dependencies/auth_dependencies.py
# This module implements authentication helper dependencies for FastAPI.
# In FastAPI, "Dependencies" are functions that are run prior to the execution of your endpoint logic.
# Here, get_current_user verifies the incoming JWT security token, ensures the user exists,
# and yields a UserResponse object. If the verification fails, it raises an HTTP 401 Unauthorized exception.

from fastapi import Header, HTTPException

from app.config.settings import settings
from app.memory.redis_memory import RedisMemoryService
from app.models.auth_models import UserResponse
from app.services.auth_service import AuthService
from app.services.token_service import TokenService

# Initialize the services needed to retrieve user status and parse tokens.
memory_service = RedisMemoryService(settings.redis_url, settings.redis_ttl_seconds)
auth_service = AuthService(memory_service)
token_service = TokenService()


def get_current_user(authorization: str = Header(default="")) -> UserResponse:
    """
    FastAPI dependency that parses and validates the 'Authorization' request header.
    
    Args:
        authorization: Passed automatically by FastAPI from the request header 'Authorization'.
                       e.g., 'Bearer <your-jwt-token>'
                       
    Returns:
        UserResponse: The validated User database object.
        
    Raises:
        HTTPException: 401 status code if the token is invalid, expired, or missing.
    """
    # 1. Enforce that the Authorization header starts with the correct scheme ("Bearer ")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token.")

    # 2. Extract the actual JWT token payload string
    token = authorization.replace("Bearer ", "", 1).strip()
    try:
        # 3. Decode the JWT token and retrieve the dictionary payload
        payload = token_service.decode_access_token(token)
        # 4. In standard JWTs, the 'sub' (subject) field holds the identifying information (user email)
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Token subject is missing.")
            
        # 5. Check if the user is present in our database
        user = auth_service.get_user(email)
        if not user:
            raise HTTPException(status_code=401, detail="User not found.")
        return user
        
    except HTTPException:
        # If an HTTP Exception was already raised, re-raise it
        raise
    except Exception as exc:
        # Catch any other decoding issues (e.g. token expired, signature mismatch) and raise an HTTP 401
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc


