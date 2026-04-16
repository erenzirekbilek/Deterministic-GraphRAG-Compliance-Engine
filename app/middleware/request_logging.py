import logging
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests and track metrics."""

    def __init__(self, app, log_requests: bool = True):
        super().__init__(app)
        self.log_requests = log_requests
        self._lock = threading.Lock()
        self._metrics = {
            "requests": defaultdict(int),
            "status_codes": defaultdict(int),
            "response_times": [],
            "total_requests": 0,
            "started_at": time.time(),
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            logger.error(f"Request error: {e}")
            raise

        duration = (time.time() - start_time) * 1000

        with self._lock:
            self._metrics["requests"][method] += 1
            self._metrics["status_codes"][status_code] += 1
            self._metrics["response_times"].append(duration)
            self._metrics["total_requests"] += 1

            if len(self._metrics["response_times"]) > 1000:
                self._metrics["response_times"] = self._metrics["response_times"][-500:]

        if self.log_requests:
            logger.info(
                f"{method} {path} | {status_code} | {duration:.2f}ms | "
                f"Client: {request.client.host if request.client else 'unknown'}"
            )

        return response

    def get_metrics(self) -> dict:
        """Get current metrics."""
        with self._lock:
            times = self._metrics["response_times"]
            avg_time = sum(times) / len(times) if times else 0
            uptime = time.time() - self._metrics["started_at"]

            return {
                "total_requests": self._metrics["total_requests"],
                "requests_by_method": dict(self._metrics["requests"]),
                "status_codes": dict(self._metrics["status_codes"]),
                "avg_response_time_ms": round(avg_time, 2),
                "uptime_seconds": round(uptime, 2),
                "requests_per_second": round(
                    self._metrics["total_requests"] / max(uptime, 1), 2
                ),
            }

    def reset_metrics(self):
        """Reset metrics counters."""
        with self._lock:
            self._metrics["requests"].clear()
            self._metrics["status_codes"].clear()
            self._metrics["response_times"].clear()
            self._metrics["total_requests"] = 0
            self._metrics["started_at"] = time.time()


class RequestLogger:
    """Class to manually log requests from services."""

    def __init__(self):
        self._lock = threading.Lock()
        self._recent_logs = []
        self._max_logs = 100

    def log(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        status: int,
        details: dict = None,
    ):
        """Log a request."""
        log_entry = {
            "timestamp": time.time(),
            "endpoint": endpoint,
            "method": method,
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "details": details or {},
        }

        with self._lock:
            self._recent_logs.append(log_entry)
            if len(self._recent_logs) > self._max_logs:
                self._recent_logs.pop(0)

    def get_recent_logs(self, limit: int = 20) -> list:
        """Get recent logs."""
        with self._lock:
            return self._recent_logs[-limit:]

    def clear_logs(self):
        """Clear logs."""
        with self._lock:
            self._recent_logs.clear()


request_logger = RequestLogger()


def log_request(
    endpoint: str, method: str, duration_ms: float, status: int, details: dict = None
):
    """Convenience function to log requests."""
    request_logger.log(endpoint, method, duration_ms, status, details)


def get_recent_logs(limit: int = 20) -> list:
    """Get recent logs."""
    return request_logger.get_recent_logs(limit)
