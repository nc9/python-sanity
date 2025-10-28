"""Exception hierarchy for Sanity Python client."""

from typing import Any


class SanityError(Exception):
    """Base exception for all Sanity errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: Any = None,
        request_details: dict[str, Any] | None = None,
    ):
        """
        Initialize Sanity error.

        :param message: Error message
        :param status_code: HTTP status code
        :param response_body: Response body from the API
        :param request_details: Details about the request (url, method, etc.)
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        self.request_details = request_details or {}

    def __str__(self) -> str:
        """Return formatted error message."""
        msg = self.message
        if self.status_code:
            msg = f"[HTTP {self.status_code}] {msg}"
        return msg


class SanityAuthError(SanityError):
    """Authentication or authorization error (401, 403)."""

    def __init__(
        self,
        message: str = "Authentication failed",
        status_code: int | None = None,
        response_body: Any = None,
        request_details: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, response_body, request_details)


class SanityNotFoundError(SanityError):
    """Resource not found error (404)."""

    def __init__(
        self,
        message: str = "Resource not found",
        status_code: int = 404,
        response_body: Any = None,
        request_details: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, response_body, request_details)


class SanityValidationError(SanityError):
    """Validation error (400)."""

    def __init__(
        self,
        message: str = "Validation failed",
        status_code: int = 400,
        response_body: Any = None,
        request_details: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, response_body, request_details)


class SanityRateLimitError(SanityError):
    """Rate limit exceeded error (429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        status_code: int = 429,
        response_body: Any = None,
        request_details: dict[str, Any] | None = None,
        retry_after: int | None = None,
    ):
        """
        Initialize rate limit error.

        :param message: Error message
        :param status_code: HTTP status code
        :param response_body: Response body from the API
        :param request_details: Details about the request
        :param retry_after: Seconds to wait before retrying (from Retry-After header)
        """
        super().__init__(message, status_code, response_body, request_details)
        self.retry_after = retry_after

    def __str__(self) -> str:
        """Return formatted error message with retry info."""
        msg = super().__str__()
        if self.retry_after:
            msg += f" (retry after {self.retry_after}s)"
        return msg


class SanityTimeoutError(SanityError):
    """Request timeout error."""

    def __init__(
        self,
        message: str = "Request timed out",
        request_details: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code=None, request_details=request_details)


class SanityServerError(SanityError):
    """Server error (5xx)."""

    def __init__(
        self,
        message: str = "Server error",
        status_code: int | None = None,
        response_body: Any = None,
        request_details: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, response_body, request_details)


class SanityConnectionError(SanityError):
    """Network connection error."""

    def __init__(
        self,
        message: str = "Connection failed",
        request_details: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code=None, request_details=request_details)


# Legacy alias for backward compatibility
class SanityIOError(SanityError):
    """Legacy exception for backward compatibility."""

    pass
