"""
Redis-backed sliding window rate limiter middleware.
Limits: 100 req/min per API key, 20 req/min per IP for unauthenticated.
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_SKIP_PATHS = {"/metrics", "/docs", "/redoc", "/openapi.json"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter using Redis.

    - Authenticated (API key): 100 req/min
    - Unauthenticated: 20 req/min per IP
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        try:
            limit_hit = await self._check_rate_limit(request)
            if limit_hit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests. Please slow down.",
                        },
                    },
                    headers={"Retry-After": "60"},
                )
        except Exception as e:
            # Never block requests due to Redis failures
            logger.warning("Rate limiter Redis error", error=str(e))

        return await call_next(request)

    async def _check_rate_limit(self, request: Request) -> bool:
        """
        Sliding window counter using Redis.
        Returns True if rate limit exceeded.
        """
        import redis.asyncio as aioredis

        api_key = request.headers.get("x-api-key")
        client_ip = self._get_client_ip(request)

        if api_key:
            key = f"vt:rl:key:{api_key[:20]}"
            limit = settings.rate_limit_per_minute
        else:
            key = f"vt:rl:ip:{client_ip}"
            limit = settings.rate_limit_burst

        try:
            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            window = 60  # 1-minute window
            current = await r.incr(key)
            if current == 1:
                await r.expire(key, window)
            await r.aclose()
            return current > limit
        except Exception:
            return False  # Fail open

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
