"""Exceptions for the MittFortum integration."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError


class MittFortumError(HomeAssistantError):
    """Base exception for MittFortum integration."""

    def __init__(self, message: str = "An error occurred") -> None:
        """Initialize the exception."""
        super().__init__(message)
        self.message = message


class AuthenticationError(MittFortumError):
    """Exception raised for authentication errors."""

    def __init__(self, message: str = "Authentication failed") -> None:
        """Initialize the exception."""
        super().__init__(message)


class APIError(MittFortumError):
    """Exception raised for API-related errors."""

    def __init__(self, message: str = "API error occurred") -> None:
        """Initialize the exception."""
        super().__init__(message)


class ConfigurationError(MittFortumError):
    """Exception raised for configuration errors."""

    def __init__(self, message: str = "Configuration error") -> None:
        """Initialize the exception."""
        super().__init__(message)


class ConnectionError(MittFortumError):
    """Exception raised for connection errors."""

    def __init__(self, message: str = "Connection error") -> None:
        """Initialize the exception."""
        super().__init__(message)


class InvalidResponseError(APIError):
    """Exception raised when API response is invalid."""

    def __init__(self, message: str = "Invalid API response") -> None:
        """Initialize the exception."""
        super().__init__(message)


class UnexpectedStatusCodeError(APIError):
    """Exception raised when API returns unexpected status code."""

    def __init__(self, message: str = "Unexpected status code") -> None:
        """Initialize the exception."""
        super().__init__(message)


class TokenExpiredError(AuthenticationError):
    """Exception raised when authentication token has expired."""

    def __init__(self, message: str = "Token has expired") -> None:
        """Initialize the exception."""
        super().__init__(message)


class OAuth2Error(AuthenticationError):
    """Exception raised for OAuth2-related errors."""

    def __init__(self, message: str = "OAuth2 error occurred") -> None:
        """Initialize the exception."""
        super().__init__(message)
