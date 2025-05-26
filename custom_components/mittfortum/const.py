"""Constants for the MittFortum integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

# Integration domain
DOMAIN = "mittfortum"

# Platforms
PLATFORMS: list[Platform] = [Platform.SENSOR]

# API endpoints
FORTUM_BASE_URL = "https://www.fortum.com/se/el"
API_BASE_URL = f"{FORTUM_BASE_URL}/api"
TRPC_BASE_URL = f"{API_BASE_URL}/trpc"
OAUTH_BASE_URL = "https://sso.fortum.com"

# Session endpoint (for customer details and metering points)
SESSION_URL = f"{API_BASE_URL}/auth/session"

# tRPC endpoints (only for time series data)
TIME_SERIES_URL = f"{TRPC_BASE_URL}/loggedIn.timeSeries.listTimeSeries"

# API request configuration
TRPC_BATCH_PARAM = "1"
DEFAULT_RESOLUTION = "MONTH"
AVAILABLE_RESOLUTIONS = ["HOUR", "DAY", "MONTH", "YEAR"]

# Energy data types
ENERGY_DATA_TYPE = "ENERGY"

# Cost component types
COST_TYPES = {
    "ELCERT_AMOUNT": "Certificate costs",
    "FIXED_FEE_AMOUNT": "Fixed fees",
    "SPOT_VARIABLE_AMOUNT": "Variable spot price",
    "VAR_AMOUNT": "Variable amount",
    "VAR_DISCOUNT_AMOUNT": "Discounts",
}

# OAuth2 configuration
OAUTH_CLIENT_ID = "swedenmypagesprod"
OAUTH_REDIRECT_URI = "https://www.mittfortum.se"
OAUTH_SECRET_KEY = "shared_secret"
OAUTH_SCOPE = ["openid", "profile", "crmdata"]

# OAuth2 endpoints
OAUTH_CONFIG_URL = f"{OAUTH_BASE_URL}/.well-known/openid-configuration"
OAUTH_TOKEN_URL = f"{OAUTH_BASE_URL}/am/oauth2/access_token"
OAUTH_AUTH_URL = f"{OAUTH_BASE_URL}/am/json/realms/root/realms/alpha/authenticate"

# Update intervals
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=30)
TOKEN_REFRESH_INTERVAL = timedelta(minutes=5)

# Device information
MANUFACTURER = "Fortum"
MODEL = "MittFortum"

# Sensor configuration
ENERGY_SENSOR_KEY = "energy_consumption"
COST_SENSOR_KEY = "total_cost"

# Data storage keys
CONF_CUSTOMER_ID = "customer_id"
CONF_METERING_POINTS = "metering_points"
