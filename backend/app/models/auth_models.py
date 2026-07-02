# models/auth_models.py
# This module defines Pydantic data models for user registration, login, and authentication responses.
# Pydantic validates incoming JSON request payloads automatically before the FastAPI endpoints run.
# If a client sends an invalid email or short password, FastAPI automatically returns an HTTP 422 Unprocessable Entity error.

from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """
    Schema for a registration request.
    EmailStr ensures the input is a syntactically valid email format (e.g. user@example.com).
    Field(min_length=6) requires the password string to contain at least 6 characters.
    """
    email: EmailStr
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    """
    Schema for a login request.
    Validates input using the same requirements as RegisterRequest.
    """
    email: EmailStr
    password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    """
    Schema returned to the user upon a successful login.
    Contains the signed JWT 'access_token', the scheme type ('bearer'), and the logged-in email.
    """
    access_token: str
    token_type: str = "bearer"
    email: EmailStr


class UserResponse(BaseModel):
    """
    Simple schema for user details, hiding sensitive fields (like hashed passwords).
    Used to return user information in the /status endpoint.
    """
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None


