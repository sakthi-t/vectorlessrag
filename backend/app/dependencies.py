import time
from fastapi import Depends, Request, HTTPException, status
import redis.asyncio as redis

from app.config import settings
from app.auth.tenant import get_tenant_context, TenantContext

_redis: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    global _redis
    if _redis is not None:
        return _redis
    try:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await _redis.ping()
        return _redis
    except Exception:
        return None


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(
        self,
        request: Request,
        ctx: TenantContext = Depends(get_tenant_context),
        r: redis.Redis | None = Depends(get_redis),
    ):
        if r is None:
            return

        key = f"ratelimit:{ctx.user_id}:{request.url.path}"
        now = time.time()
        window_start = now - self.window_seconds

        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, self.window_seconds + 1)
        _, count, _, _ = await pipe.execute()

        if count >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds}s.",
            )


chat_rate_limit = RateLimiter(max_requests=60, window_seconds=60)
upload_rate_limit = RateLimiter(max_requests=10, window_seconds=3600)
