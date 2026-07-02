# middleware/security_headers_middleware.py
# This module implements the SecurityHeadersMiddleware.
# Adding security headers to HTTP responses is a web security best practice.
# These headers instruct the browser on how to restrict certain client-side activities (such as loading external scripts,
# displaying our app inside an iframe, or accessing sensitive browser hardware APIs like the camera or microphone).

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    SecurityHeadersMiddleware appends safety-focused HTTP headers to every response sent to the client.
    Helps protect clients against Clickjacking, XSS (Cross-Site Scripting), and mime-sniffing.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Await the processing of the request by the rest of the application
        response = await call_next(request)
        
        # 1. X-Frame-Options: Prevents clickjacking by instructing the browser that this site
        # should never be rendered inside an iframe, frame, or object tag on another domain.
        response.headers["X-Frame-Options"] = "DENY"
        
        # 2. X-Content-Type-Options: Prevents MIME-type sniffing. This forces the browser to respect
        # the Content-Type header sent by the server, rather than trying to guess the file type and run it.
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # 3. X-XSS-Protection: Activates XSS filtering in older browsers. "1; mode=block" instructs
        # the browser to completely block rendering of the page if a cross-site scripting attack is detected.
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # 4. Referrer-Policy: Controls how much referrer information is sent along with HTTP requests.
        # "strict-origin-when-cross-origin" sends the full URL when making same-origin requests, but only the domain name for cross-origin requests.
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 5. Content-Security-Policy (CSP): Restricts which domains are allowed to load scripts, styles, images, and fonts.
        # This is a major defense against Cross-Site Scripting (XSS) attacks.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "                                    # Default rule: only load resources from our own host
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "        # Allow scripts from our host, along with inline and evaluated javascript (needed for many frameworks)
            "style-src 'self' 'unsafe-inline'; "                      # Allow styles from our host and inline CSS
            "img-src 'self' data: https:; "                           # Allow images from our host, base64 data URIs, and secure https websites
            "font-src 'self' data:; "                                 # Allow fonts from our host and inline base64
            "connect-src 'self'"                                      # Limit API connection endpoints (AJAX/Fetch) only to our own host
        )
        
        # 6. Permissions-Policy: Restricts browser feature access for security/privacy.
        # Setting features to () blocks this site and any embedded iframes from accessing hardware or APIs (like camera, microphone, etc.).
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        return response
