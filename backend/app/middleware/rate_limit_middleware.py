# middleware/rate_limit_middleware.py
# This module implements an in-memory Rate Limiting middleware.
# Rate limiting limits the number of requests a single client (identified by their IP address)
# can make to our server within a certain window of time (e.g. 60 requests per minute).
# This helps protect our backend resources from being overwhelmed by spam, bots, or accidental infinite loops.

import logging
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
# JSONResponse allows us to return custom, structured JSON error bodies directly.
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple sliding-window in-memory rate limiting middleware.
    
    Warning: This is stored in-memory. If the server restarts or if we run multiple server processes
    (horizontal scaling), the request counts reset or are not shared. For production apps,
    it is best to store these request counts in a distributed cache like Redis.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        # We must initialize the base class BaseHTTPMiddleware with the FastAPI app instance.
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        # request_counts maps: IP Address (str) -> List of floating-point timestamps (list of epoch times)
        # defaultdict(list) automatically initializes an empty list [] if we look up a new IP.
        self.request_counts = defaultdict(list)
        # Interval to clean up stale IP listings from memory (every 60 seconds)
        self.cleanup_interval = 60  
        self.last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Determine the client's IP address. If not visible, fall back to "unknown".
        client_ip = request.client.host if request.client else "unknown"
        
        # Bypass rate limiting for the /health router. We want uptime monitors to always be able to reach it.
        if request.url.path == "/health":
            return await call_next(request)
        
        current_time = time.time()
        # Periodically clean up very old IP history to avoid consuming too much RAM memory.
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(current_time)
            self.last_cleanup = current_time
        
        # Fetch the list of timestamps when this client IP previously made requests
        timestamps = self.request_counts[client_ip]
        
        # Calculate the start of our 60-second window
        cutoff_time = current_time - 60
        # Filter out all timestamps that occurred before the current 60-second window
        timestamps[:] = [ts for ts in timestamps if ts > cutoff_time]
        
        # Check if the client has hit or exceeded the allowed request limit
        if len(timestamps) >= self.requests_per_minute:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "requests_in_window": len(timestamps),
                    "limit": self.requests_per_minute,
                },
            )
            # Return an HTTP 429 Too Many Requests response immediately, skipping the request execution.
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60, # Tells client how many seconds to wait before retrying
                },
                headers={"Retry-After": "60"},
            )
        
        # Record the current request's timestamp in the IP's history
        timestamps.append(current_time)
        
        # Proceed with executing the request
        response = await call_next(request)
        
        # Append rate-limiting metadata headers to the HTTP response.
        # This informs frontends/clients of their current rate-limit usage status.
        remaining = self.requests_per_minute - len(timestamps)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))
        
        return response

    def _cleanup_old_entries(self, current_time: float):
        """
        Removes entries for client IPs that haven't made any requests in the last 5 minutes.
        This prevents memory leaks from temporary client connections.
        """
        cutoff_time = current_time - 300  # 5 minutes ago
        ips_to_remove = []
        
        # Identify inactive IPs
        for ip, timestamps in self.request_counts.items():
            if not timestamps or max(timestamps) < cutoff_time:
                ips_to_remove.append(ip)
        
        # Remove them from the dictionary
        for ip in ips_to_remove:
            del self.request_counts[ip]
        
        if ips_to_remove:
            logger.debug(f"Cleaned up rate limit data for {len(ips_to_remove)} IPs")


