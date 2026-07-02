# main.py is the main entry point of our FastAPI application.
# It initializes the FastAPI application, configures global middlewares (such as CORS, rate limiting, and security headers),
# sets up logging, and registers the routers that handle individual API endpoints.

import logging
import os

# Import the settings object which reads configurations from the environment (.env file)
from app.config.settings import settings

# FastAPI is a modern, fast (high-performance) web framework for building APIs with Python.
from fastapi import FastAPI

# CORSMiddleware allows our API to accept requests from web applications hosted on other domains (like a React or Vue frontend).
from fastapi.middleware.cors import CORSMiddleware

# Import our custom logging configuration handler to ensure log formatting remains unified and searchable
from app.logging_config import configure_uvicorn_logging

# Import custom middlewares we created to secure, rate limit, and log incoming API requests.
# Middleware functions act as 'gatekeepers' that process requests before they reach our routes,
# and process responses before they go back to the client.
from app.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)

# Import individual routers (endpoints grouped by feature/logical scope)
from app.routers.auth_router import router as auth_router
from app.routers.health_router import router as health_router
from app.routers.ingest_router import router as ingest_router
from app.routers.chat_router import router as chat_router
from app.routers.files_router import router as files_router

# Configure uvicorn's internal logging so it matches our application's formatting style
configure_uvicorn_logging()
# Get a logger instance for this module using its python path name
logger = logging.getLogger(__name__)

# Instantiate the FastAPI app. This 'app' object will be run by Uvicorn (the web server).
app = FastAPI(
    title=settings.app_name,
    version="0.0.1",
    description="Starter multi-agent backend with auth, Redis memory, Supabase pgvector search, and router-based modular structure."
)

# Register middlewares in the FastAPI app stack.
# Note: FastAPI executes middlewares in the reverse order of registration for responses,
# and in order of registration for requests.
# 1. SecurityHeadersMiddleware injects secure HTTP headers (e.g. X-Content-Type-Options) to protect against common web attacks.
app.add_middleware(SecurityHeadersMiddleware)

# 2. RateLimitMiddleware prevents API abuse by limiting each client to 60 requests per minute.
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# 3. LoggingMiddleware captures details of incoming requests (method, URL, timing) and logs them.
app.add_middleware(LoggingMiddleware)

# 4. CORSMiddleware configuration to control which frontends can connect to this backend.
app.add_middleware(
    CORSMiddleware,
    # Allow lists defined in environment variables (e.g., http://localhost:3000)
    allow_origins=settings.backend_cors_origins,
    # Credentials allow cookies/session tokens to be sent along with cross-origin requests
    allow_credentials=True,
    # Allow any HTTP method (GET, POST, PUT, DELETE, etc.)
    allow_methods=["*"],
    # Allow any HTTP header (Authorization, Content-Type, etc.)
    allow_headers=["*"],
)

# Include the routers. Each router acts like a sub-application focusing on a specific path prefix.
# Health router is for checkups (checking if server is alive).
app.include_router(health_router)
# Auth router handles registration, login, and profile operations.
app.include_router(auth_router)
# Files router handles listing, fetching, and deleting user-uploaded files.
app.include_router(files_router)
# Ingest router processes files (PDFs, CSVs) and indexes them into Supabase pgvector.
app.include_router(ingest_router)
# Chat router coordinates user messages, the supervisor, and worker agents.
app.include_router(chat_router)

# Log a message indicating the app has started up successfully, passing extra metadata
# to be formatted nicely by our logger (JSON or text).
logger.info(
    "Application startup configured.",
    extra={
        "app_name": settings.app_name,
        "api_prefix": settings.api_prefix,
        "llm_provider": settings.llm_provider,
        "elastic_index": settings.elasticsearch_index,
    },
)
# Trigger reload