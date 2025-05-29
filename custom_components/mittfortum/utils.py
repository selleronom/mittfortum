"""Utilities for MittFortum integration."""

from __future__ import annotations

from typing import Any

import jwt


def extract_customer_id_from_token(id_token: str) -> str:
    """Extract customer ID from JWT ID token."""
    try:
        payload = jwt.decode(id_token, options={"verify_signature": False})
        return payload["customerid"][0]["crmid"]
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError(f"Failed to extract customer ID from token: {exc}") from exc


def safe_get_nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary values."""
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def format_currency(amount: float | None, currency: str = "SEK") -> str:
    """Format currency amount."""
    if amount is None:
        return f"0.00 {currency}"
    return f"{amount:.2f} {currency}"


def format_energy(amount: float | None, unit: str = "kWh") -> str:
    """Format energy amount."""
    if amount is None:
        return f"0.00 {unit}"
    return f"{amount:.2f} {unit}"
