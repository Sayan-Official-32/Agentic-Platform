# prompts/__init__.py
# This file initializes the prompts package.
# It exposes the centralized prompt repository classes like LLMPrompts for other services.

from .llm_prompts import LLMPrompts

__all__ = ["LLMPrompts"]