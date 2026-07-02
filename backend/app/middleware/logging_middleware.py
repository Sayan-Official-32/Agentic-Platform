# middleware/logging_middleware.py
# This module contains our custom LoggingMiddleware, which intercepts every incoming HTTP request
# and outgoing response in our application. It measures how long a request takes to process (in milliseconds),
# generates a unique request ID to track the request throughout its lifecycle, and logs the outcome (success or failure).

import logging
import time
import uuid
from typing import Callable

# FastAPI's Request and Response objects represent the HTTP data coming from the client and going back to the client.
from fastapi import Request, Response
# BaseHTTPMiddleware is the base class provided by Starlette/FastAPI to easily build custom middlewares.
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    LoggingMiddleware hooks into the FastAPI request-response pipeline.
    It logs standard information for all API calls.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        The dispatch method receives the incoming 'request' and a function 'call_next'
        representing the next middleware/route handler in the pipeline.
        """
        # Generate a unique request identifier (UUID) to group logs relating to this specific call.
        request_id = str(uuid.uuid4())
        
        # Attach the request ID to the request state so downstream handlers or endpoints can access it if needed.
        request.state.request_id = request_id
        
        # Log metadata about the request before we process it.
        logger.info(
            "Incoming request",
            extra={
                "request_id": request_id,
                "method": request.method,               # GET, POST, etc.
                "path": request.url.path,               # e.g., /api/v1/chat
                "client_host": request.client.host if request.client else None, # Client IP address
                "user_agent": request.headers.get("user-agent"),               # Browser or client library info
            },
        )
        
        # Record the start time to calculate response latency
        start_time = time.time()
        
        try:
            # call_next(request) passes the request to the rest of the application.
            # It returns the generated 'response' object asynchronously.
            response = await call_next(request)
            
            # Calculate the processing duration (latency)
            duration = time.time() - start_time
            
            # Inject the request ID into the HTTP response headers so the client/frontend
            # can report it if they encounter errors (great for debugging!).
            response.headers["X-Request-ID"] = request_id
            
            # Log the successful completion of the request
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,           # 200, 404, 500, etc.
                    "duration_ms": round(duration * 1000, 2),      # Convert seconds to milliseconds
                },
            )
            
            return response
            
        except Exception as e:
            # If the application throws an unhandled exception, calculate latency and log the error.
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2),
                },
                exc_info=True, # Attaches the full python traceback stack trace to the log
            )
            # Re-raise the exception so FastAPI can handle it (returning a 500 Internal Server Error to the user)
            raise


