"""
Custom exception classes and global FastAPI exception handlers.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose import JWTError

from app.core.logging import get_logger

logger = get_logger(__name__)


# ─── Base Exception ───────────────────────────────────────────────────────────
class VeriTrustException(Exception):  # noqa: N818
    """Base exception for all VeriTrust application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


# ─── Auth Exceptions ──────────────────────────────────────────────────────────
class AuthenticationError(VeriTrustException):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, "AUTHENTICATION_ERROR")


class InvalidTokenError(VeriTrustException):
    def __init__(self, message: str = "Invalid or expired token") -> None:
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, "INVALID_TOKEN")


class InsufficientPermissionsError(VeriTrustException):
    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message, status.HTTP_403_FORBIDDEN, "INSUFFICIENT_PERMISSIONS")


# ─── Resource Exceptions ──────────────────────────────────────────────────────
class NotFoundError(VeriTrustException):
    def __init__(self, resource: str = "Resource", resource_id: str | None = None) -> None:
        msg = f"{resource} not found"
        if resource_id:
            msg = f"{resource} '{resource_id}' not found"
        super().__init__(msg, status.HTTP_404_NOT_FOUND, "NOT_FOUND")


class ConflictError(VeriTrustException):
    def __init__(self, message: str = "Resource already exists") -> None:
        super().__init__(message, status.HTTP_409_CONFLICT, "CONFLICT")


# ─── Validation Exceptions ────────────────────────────────────────────────────
class ValidationError(VeriTrustException):
    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR")


# ─── Business Logic Exceptions ────────────────────────────────────────────────
class OrganizationInactiveError(VeriTrustException):
    def __init__(self) -> None:
        super().__init__("Organization is inactive", status.HTTP_403_FORBIDDEN, "ORG_INACTIVE")


class APIKeyInvalidError(VeriTrustException):
    def __init__(self) -> None:
        super().__init__(
            "Invalid or revoked API key", status.HTTP_401_UNAUTHORIZED, "API_KEY_INVALID"
        )


class RateLimitExceededError(VeriTrustException):
    def __init__(self) -> None:
        super().__init__(
            "Rate limit exceeded. Please slow down.",
            status.HTTP_429_TOO_MANY_REQUESTS,
            "RATE_LIMIT_EXCEEDED",
        )


# ─── Exception Handlers ───────────────────────────────────────────────────────
def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: list | None = None,
) -> JSONResponse:
    body: dict = {"success": False, "error": {"code": error_code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(VeriTrustException)
    async def veritrust_exception_handler(
        request: Request, exc: VeriTrustException
    ) -> JSONResponse:
        logger.warning(
            "Application exception",
            error_code=exc.error_code,
            message=exc.message,
            path=str(request.url),
        )
        return _error_response(exc.status_code, exc.error_code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": " -> ".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
                "type": err["type"],
            }
            for err in exc.errors()
        ]
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            "Request validation failed",
            details,
        )

    @app.exception_handler(JWTError)
    async def jwt_exception_handler(request: Request, exc: JWTError) -> JSONResponse:
        return _error_response(
            status.HTTP_401_UNAUTHORIZED, "INVALID_TOKEN", "Invalid or expired token"
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            exc_type=type(exc).__name__,
            exc_message=str(exc),
            path=str(request.url),
        )
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "An unexpected error occurred",
        )
