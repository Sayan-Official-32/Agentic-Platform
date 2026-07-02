# services/token_service.py
# This module implements the TokenService class.
# It handles creating (encoding) and verifying (decoding) JSON Web Tokens (JWTs).
# JWTs are stateless security credentials. Instead of storing session records on the server,
# we cryptographically sign user information (email, expiration) and send it as a string token.
# The client sends this token with each API request, and the server verifies the signature to authorize them.

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt

from app.config.settings import settings

class TokenService:
    def create_access_token(self, subject: str) -> str:
        """
        Creates a signed JWT token containing the subject (user's email) and an expiration timestamp.
        """
        # 1. Set the expiration timestamp based on our configuration settings.
        # datetime.now(timezone.utc) ensures we use timezone-independent UTC timestamps.
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.auth_token_expiry_minutes)
        
        # 2. Build the token payload dictionary.
        # "sub" (subject) represents the unique identifier of the user (e.g. email).
        # "exp" (expiration claim) tells libraries when this token becomes invalid.
        payload: Dict[str, Any] = {
            "sub": subject,
            "exp": expires_at,
        }
        
        # 3. Cryptographically sign the payload.
        # jwt.encode takes the payload, signs it using a secret password key, and registers the algorithm (HS256).
        return jwt.encode(payload, settings.auth_secret_key, algorithm=settings.auth_algorithm)

    def decode_access_token(self, token: str) -> Dict[str, Any]:
        """
        Decodes and verifies a JWT token.
        If the signature is invalid or the expiration time ('exp') has passed,
        this will automatically raise an exception (like jwt.ExpiredSignatureError).
        """
        return jwt.decode(token, settings.auth_secret_key, algorithms=[settings.auth_algorithm])