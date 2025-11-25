# app/middleware/security.py
import re
import time
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable


class SecurityMiddleware(BaseHTTPMiddleware):
    """Protects against SQL injection, XSS, CSRF, DDoS, and other attacks"""
    
    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.sql_patterns = [
            r"(\bunion\b.*\bselect\b)", r"(\bselect\b.*\bfrom\b)",
            r"(\binsert\b.*\binto\b)", r"(\bdelete\b.*\bfrom\b)",
            r"(\bdrop\b.*\btable\b)", r"(--)", r"(\bor\b.*=.*)"
        ]
        self.xss_patterns = [
            r"<script[^>]*>", r"javascript:", r"onerror=", r"onload=", r"<iframe"
        ]
        self.request_counts = {}
        self.cleanup_counter = 0
    
    async def dispatch(self, request: Request, call_next: Callable):
        # SQL Injection Protection
        if await self._detect_sql_injection(request):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid request"}
            )
        
        # XSS Protection
        if self._detect_xss(str(request.url.query)):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid content"}
            )
        
        # CSRF Protection
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            if not self._validate_csrf(request):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "CSRF validation failed"}
                )
        
        # Request Size Limit (10MB)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request too large"}
            )
        
        # Rate Limiting
        if not self._check_rate_limit(request.client.host):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests"}
            )
        
        response = await call_next(request)
        
        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response
    
    async def _detect_sql_injection(self, request: Request) -> bool:
        query = str(request.url.query).lower()
        for pattern in self.sql_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False
    
    def _detect_xss(self, text: str) -> bool:
        for pattern in self.xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _validate_csrf(self, request: Request) -> bool:
        # Skip CSRF for API endpoints (JSON content type)
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            return True
        
        # Skip CSRF for authenticated requests
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            return True
            
        # Require CSRF token for form submissions
        return bool(request.headers.get("x-csrf-token"))
    
    def _check_rate_limit(self, ip: str) -> bool:
        minute = int(time.time() / 60)
        key = f"{ip}:{minute}"
        
        # Periodic cleanup to prevent memory leak
        self.cleanup_counter += 1
        if self.cleanup_counter > 1000:
            self.request_counts = {k: v for k, v in self.request_counts.items() if k.split(':')[1] == str(minute)}
            self.cleanup_counter = 0
        
        self.request_counts[key] = self.request_counts.get(key, 0) + 1
        return self.request_counts[key] <= 1000


class InputSanitizer:
    """Sanitize user inputs"""
    
    @staticmethod
    def sanitize_string(value: str) -> str:
        if not value:
            return value
        value = value.replace('\x00', '')
        return ''.join(c for c in value if ord(c) >= 32 or c in '\n\r\t').strip()
    
    @staticmethod
    def sanitize_phone(phone: str) -> str:
        return re.sub(r'[^\d+\-\s()]', '', phone)
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        return re.sub(r'[^\w\.\-@]', '', email).lower()


class PasswordValidator:
    """Validate password strength"""
    
    @staticmethod
    def validate(password: str) -> tuple:
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain uppercase"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain lowercase"
        if not re.search(r'\d', password):
            return False, "Password must contain number"
        if password.lower() in ['password', '12345678', 'qwerty']:
            return False, "Password too common"
        return True, "Valid"