"""API endpoints configuration."""

from __future__ import annotations

import json
import urllib.parse
from datetime import datetime

from ..const import (
    OAUTH_AUTH_URL,
    OAUTH_CONFIG_URL,
    OAUTH_TOKEN_URL,
    TIME_SERIES_URL,
)


class APIEndpoints:
    """API endpoints configuration."""

    # OAuth2 endpoints
    OPENID_CONFIG = OAUTH_CONFIG_URL
    AUTH_INIT = (
        f"{OAUTH_AUTH_URL}?locale=sv&authIndexType=service&authIndexValue=SeB2COGWLogin"
    )
    TOKEN_EXCHANGE = OAUTH_TOKEN_URL
    USER_SESSION = "https://sso.fortum.com/am/json/users?_action=idFromSession"
    THEME_REALM = "https://sso.fortum.com/openidm/config/ui/themerealm"
    USER_DETAILS = (
        "https://sso.fortum.com/am/json/realms/root/realms/alpha/users/{user_id}"
    )
    VALIDATE_GOTO = "https://sso.fortum.com/am/json/realms/root/realms/alpha/users?_action=validateGoto"
    SESSION_USERNAME = "https://www.fortum.com/se/el/api/get-session-username"
    SESSION = "https://www.fortum.com/se/el/api/auth/session"

    # tRPC API endpoints
    TIME_SERIES = TIME_SERIES_URL

    @staticmethod
    def get_time_series_url(
        metering_point_nos: list[str],
        from_date: datetime,
        to_date: datetime,
        resolution: str = "MONTH",
    ) -> str:
        """Get time series URL with tRPC format."""
        input_data = {
            "0": {
                "json": {
                    "meteringPointNo": metering_point_nos,
                    "fromDate": from_date.isoformat() + "Z",
                    "toDate": to_date.isoformat() + "Z",
                    "resolution": resolution,
                }
            }
        }

        input_json = json.dumps(input_data, separators=(",", ":"))
        input_encoded = urllib.parse.quote(input_json)

        return f"{APIEndpoints.TIME_SERIES}?batch=1&input={input_encoded}"

    @staticmethod
    def get_user_details_url(user_id: str) -> str:
        """Get user details URL."""
        return APIEndpoints.USER_DETAILS.format(user_id=user_id)
