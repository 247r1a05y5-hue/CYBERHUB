"""Custom exceptions used throughout the application."""
from __future__ import annotations


class CyberPlatformError(Exception):
    """Base exception."""


class NotFoundError(CyberPlatformError):
    """Resource not found (maps to 404)."""


class AuthenticationError(CyberPlatformError):
    """Authentication failed (maps to 401)."""


UnauthorizedError = AuthenticationError


class AuthorizationError(CyberPlatformError):
    """Authorization failed (maps to 403)."""


ForbiddenError = AuthorizationError


class ConflictError(CyberPlatformError):
    """Resource conflict (maps to 409)."""


class ValidationError(CyberPlatformError):
    """Business rule validation failed (maps to 422)."""


class InvalidTransitionError(CyberPlatformError):
    """Attempted an invalid state machine transition."""


class RateLimitError(CyberPlatformError):
    """Rate limit exceeded (maps to 429)."""


class StorageError(CyberPlatformError):
    """File storage operation failed."""


class AnalyzerError(CyberPlatformError):
    """Analyzer execution failed."""
