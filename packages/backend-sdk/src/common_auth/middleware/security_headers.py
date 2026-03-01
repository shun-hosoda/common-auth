"""Security headers middleware."""

import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Headers added:
    - Strict-Transport-Security (HSTS)
    - Content-Security-Policy (CSP)
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """

    DEFAULT_HEADERS = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "0",  # Disabled in favor of CSP
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }

    def __init__(self, app, custom_headers: dict[str, str] | None = None) -> None:
        """
        Initialize security headers middleware.
        
        Args:
            app: FastAPI application
            custom_headers: Optional custom headers to override defaults
        """
        super().__init__(app)
        self.headers = {**self.DEFAULT_HEADERS}
        if custom_headers:
            self.headers.update(custom_headers)
        logger.info("Initialized SecurityHeadersMiddleware")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response with security headers
        """
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.headers.items():
            response.headers[header] = value
        
        return response
