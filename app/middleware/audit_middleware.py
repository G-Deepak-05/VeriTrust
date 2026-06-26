"""
Audit middleware — captures request context for every API call.
Non-blocking: dispatches audit events to Celery.
"""
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)

# Endpoints to skip auditing (noisy, low-value)
_SKIP_PATHS = {"/metrics", "/docs", "/redoc", "/openapi.json", "/api/v1/health"}


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that captures key request metadata for audit logs.
    Audit events are dispatched to Celery (fire-and-forget) to avoid
    adding latency to the critical path.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        # Async audit dispatch — never block the response
        try:
            self._dispatch_audit(request, response.status_code, duration_ms)
        except Exception:
            pass  # Audit failures must NEVER affect the API response

        return response

    def _dispatch_audit(
        self, request: Request, status_code: int, duration_ms: int
    ) -> None:
        """Dispatch audit event to Celery (non-blocking)."""
        try:
            from app.workers.tasks import write_audit_log_task

            # Extract auth context from request state (set by dependency)
            actor_id = getattr(request.state, "user_id", None)
            org_id = getattr(request.state, "org_id", None)

            write_audit_log_task.delay(
                action=f"{request.method.lower()}.{request.url.path.strip('/').replace('/', '.')}",
                endpoint=str(request.url.path),
                method=request.method,
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("user-agent", ""),
                actor_id=str(actor_id) if actor_id else None,
                org_id=str(org_id) if org_id else None,
                status="success" if status_code < 400 else "error",
                metadata={"status_code": status_code, "duration_ms": duration_ms},
            )
        except Exception as e:
            logger.debug("Failed to dispatch audit log", error=str(e))

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract real client IP, respecting X-Forwarded-For."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
