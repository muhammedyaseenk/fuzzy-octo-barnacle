# app/core/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request
from app.core.config import settings

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_REQUESTS}/minute"]
)


def init_rate_limiter(app: FastAPI):
    """Initialize rate limiter with FastAPI app"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Common rate limit decorators
def auth_rate_limit():
    """Rate limit for authentication endpoints"""
    return limiter.limit("5/minute")


def api_rate_limit():
    """Rate limit for general API endpoints"""
    return limiter.limit("100/minute")


def upload_rate_limit():
    """Rate limit for upload endpoints"""
    return limiter.limit("10/minute")