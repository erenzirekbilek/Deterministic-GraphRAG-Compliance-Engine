import time
import logging
from typing import Callable, Dict, Tuple
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class RateLimiter(BaseHTTPMiddleware):
    """Rate limiting middleware using token bucket algorithm."""

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size

        self._lock = threading.Lock()
        self._minute_buckets: Dict[str, Tuple[int, float]] = {}
        self._hour_buckets: Dict[str, Tuple[int, float]] = {}
        self._daily_buckets: Dict[str, Tuple[int, float]] = {}

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        if request.client:
            return request.client.host
        return "unknown"

    def _cleanup_old_entries(self):
        """Remove expired entries from buckets."""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        day_ago = now - 86400

        with self._lock:
            self._minute_buckets = {
                k: v for k, v in self._minute_buckets.items() if v[1] > minute_ago
            }
            self._hour_buckets = {
                k: v for k, v in self._hour_buckets.items() if v[1] > hour_ago
            }
            self._daily_buckets = {
                k: v for k, v in self._daily_buckets.items() if v[1] > day_ago
            }

    def _check_rate_limit(self, client_id: str) -> Tuple[bool, str]:
        """Check if request is within rate limits."""
        now = time.time()

        with self._lock:
            if client_id in self._minute_buckets:
                count, timestamp = self._minute_buckets[client_id]
                if now - timestamp < 60:
                    if count >= self.requests_per_minute:
                        return (
                            False,
                            f"Rate limit: {self.requests_per_minute} requests per minute",
                        )
                    self._minute_buckets[client_id] = (count + 1, timestamp)
                else:
                    self._minute_buckets[client_id] = (1, now)
            else:
                self._minute_buckets[client_id] = (1, now)

            if client_id in self._hour_buckets:
                count, timestamp = self._hour_buckets[client_id]
                if now - timestamp < 3600:
                    if count >= self.requests_per_hour:
                        return (
                            False,
                            f"Rate limit: {self.requests_per_hour} requests per hour",
                        )
                    self._hour_buckets[client_id] = (count + 1, timestamp)
                else:
                    self._hour_buckets[client_id] = (1, now)
            else:
                self._hour_buckets[client_id] = (1, now)

        self._cleanup_old_entries()
        return True, ""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_id = self._get_client_id(request)

        allowed, message = self._check_rate_limit(client_id)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_id}: {message}")
            raise HTTPException(status_code=429, detail=message)

        response = await call_next(request)

        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)

        return response


class SimpleRateLimiter:
    """Simple rate limiter for specific endpoints."""

    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self._lock = threading.Lock()
        self._requests = defaultdict(list)

    async def check(self, request: Request) -> bool:
        """Check if request is allowed."""
        client_id = request.client.host if request.client else "unknown"
        now = time.time()

        with self._lock:
            if client_id in self._requests:
                self._requests[client_id] = [
                    t for t in self._requests[client_id] if now - t < 60
                ]

                if len(self._requests[client_id]) >= self.requests_per_minute:
                    return False

                self._requests[client_id].append(now)
            else:
                self._requests[client_id] = [now]

        return True

    def reset(self, client_id: str = None):
        """Reset rate limit for client or all."""
        with self._lock:
            if client_id:
                if client_id in self._requests:
                    del self._requests[client_id]
            else:
                self._requests.clear()
