# utils/security.py
# This module provides utilities for hashing and verifying passwords securely.
# Storing plain-text passwords in databases is a major security risk.
# Instead, we run passwords through a one-way mathematical function called a "hash".
# When a user registers, we store the hash. When they log in, we hash their input password
# and compare it with the stored hash. We use passlib with the 'pbkdf2_sha256' algorithm.

from passlib.context import CryptContext

# CryptContext manages password hashing algorithms.
# schemes=["pbkdf2_sha256"] specifies that we use the PBKDF2 algorithm with SHA-256 signatures.
# deprecated="auto" handles automatic upgrading if we configure newer algorithms in the future.
password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Encrypts a clear-text password using a one-way secure hash function.
    """
    return password_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Compares a clear-text password input against a previously hashed password.
    Returns True if they match, False otherwise.
    """
    return password_context.verify(password, hashed_password)


