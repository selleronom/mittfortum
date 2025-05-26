"""Exceptions for the MittFortum integration."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError


class MittFortumError(HomeAssistantError):
    """Base exception for MittFortum integration."""


class AuthenticationError(MittFortumError):
    """Exception raised for authentication errors."""


class APIError(MittFortumError):
    """Exception raised for API-related errors."""


class ConfigurationError(MittFortumError):
    """Exception raised for configuration errors."""


class ConnectionError(MittFortumError):
    """Exception raised for connection errors."""


class InvalidResponseError(APIError):
    """Exception raised when API response is invalid."""


class UnexpectedStatusCodeError(APIError):
    """Exception raised when API returns unexpected status code."""


class TokenExpiredError(AuthenticationError):
    """Exception raised when authentication token has expired."""


class OAuth2Error(AuthenticationError):
    """Exception raised for OAuth2-related errors."""
