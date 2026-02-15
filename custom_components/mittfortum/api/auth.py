"""OAuth2 authentication client for MittFortum."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
import os
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlencode, urlparse

from homeassistant.helpers.httpx_client import get_async_client

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from ..const import OAUTH_CLIENT_ID, OAUTH_REDIRECT_URI, OAUTH_SCOPE, OAUTH_SECRET_KEY
from ..exceptions import AuthenticationError, OAuth2Error
from ..models import AuthTokens
from .endpoints import APIEndpoints

_LOGGER = logging.getLogger(__name__)

# Constants
CONTENT_TYPE_JSON = "application/json"
AUTHORIZATION_CODE_PARAM = "code="
SESSION_BASED_TOKEN = "session_based"
BEARER_TOKEN_TYPE = "Bearer"
DEFAULT_TOKEN_EXPIRY_HOURS = (
    1  # 1 hour default expiry (unused due to server bug workaround)
)
FIXED_TOKEN_LIFETIME_SECONDS = 900  # 15 minutes - workaround for server bug
URGENT_RENEWAL_THRESHOLD_SECONDS = 120  # 2 minutes - reduced for shorter tokens
DEFAULT_RENEWAL_BUFFER_SECONDS = 120  # 2 minutes - reduced for shorter tokens


class OAuth2AuthClient:
    """OAuth2 authentication client for Fortum API."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        client_id: str = OAUTH_CLIENT_ID,
        redirect_uri: str = OAUTH_REDIRECT_URI,
        secret_key: str = OAUTH_SECRET_KEY,
    ) -> None:
        """Initialize OAuth2 client."""
        self._hass = hass
        self._username = username
        self._password = password
        self._client_id = client_id
        self._redirect_uri = redirect_uri
        self._secret_key = secret_key

        # Token storage
        self._tokens: AuthTokens | None = None
        self._token_expiry: float | None = None
        self._session_data: dict[str, Any] | None = None
        self._session_cookies: dict[str, str] = {}

        # Background token monitoring
        self._token_monitor_task: asyncio.Task | None = None
        self._monitoring_enabled: bool = False

    @property
    def access_token(self) -> str | None:
        """Get current access token."""
        return self._tokens.access_token if self._tokens else None

    @property
    def refresh_token(self) -> str | None:
        """Get current refresh token."""
        return self._tokens.refresh_token if self._tokens else None

    @property
    def id_token(self) -> str | None:
        """Get current ID token."""
        return self._tokens.id_token if self._tokens else None

    @property
    def session_data(self) -> dict[str, Any] | None:
        """Get current session data."""
        return self._session_data

    @property
    def session_cookies(self) -> dict[str, str]:
        """Get current session cookies."""
        return self._session_cookies

    def is_token_expired(self, buffer_seconds: int = 0) -> bool:
        """Check if the current token is expired or will expire soon.

        Args:
            buffer_seconds: Number of seconds before actual expiry to consider
                the token expired. This allows for proactive renewal.
                Default is 0 for backwards compatibility.
        """
        if not self._token_expiry:
            _LOGGER.debug(
                "Token expiry check: No token expiry set, considering expired"
            )
            return True

        current_time = time.time()
        # Add buffer time for proactive renewal
        effective_expiry = self._token_expiry - buffer_seconds
        is_expired = current_time >= effective_expiry

        if buffer_seconds > 0:
            _LOGGER.debug(
                "Token expiry check (with %ds buffer): current_time=%.2f, "
                "token_expiry=%.2f, effective_expiry=%.2f, expired=%s "
                "(diff=%.2f seconds)",
                buffer_seconds,
                current_time,
                self._token_expiry,
                effective_expiry,
                is_expired,
                current_time - effective_expiry,
            )
        else:
            _LOGGER.debug(
                "Token expiry check: current_time=%.2f, token_expiry=%.2f, "
                "expired=%s (diff=%.2f seconds)",
                current_time,
                self._token_expiry,
                is_expired,
                current_time - self._token_expiry,
            )
        return is_expired

    def needs_renewal(self) -> bool:
        """Check if the token needs proactive renewal (2 minutes before expiry)."""
        return self.is_token_expired(buffer_seconds=DEFAULT_RENEWAL_BUFFER_SECONDS)

    def time_until_expiry(self) -> float:
        """Get time in seconds until token expires. Returns 0 if already expired."""
        if not self._token_expiry:
            return 0
        return max(0, self._token_expiry - time.time())

    def _process_token_expiry(self, expires_str: str | None) -> int:
        """Process token expiry string and return validated expires_in seconds.

        WORKAROUND: Due to server bug where all refreshed tokens get the same
        stale expiry timestamp (e.g., "2025-06-01T16:30:44.000Z"), we ignore
        the server's expiry field and use a fixed 15-minute (900 seconds)
        token lifetime. This prevents continuous re-authentication loops.

        Args:
            expires_str: The expiry string from the server, or None (ignored)

        Returns:
            Fixed 900 seconds (15 minutes) until token expires
        """
        # Log the server's broken expiry for debugging purposes
        if expires_str:
            _LOGGER.debug(
                "Server provided token expiry: '%s' (IGNORED due to server bug)",
                expires_str,
            )

            # Still parse it for comparison logging
            try:
                expires_dt = self._parse_server_datetime(expires_str)
                current_time_utc = datetime.now(UTC)
                time_diff = expires_dt - current_time_utc
                expires_in_raw = int(time_diff.total_seconds())

                _LOGGER.debug(
                    "Server expiry would be: %d seconds (%.1f minutes) - "
                    "but using fixed %d seconds (%.1f minutes) instead",
                    expires_in_raw,
                    expires_in_raw / 60,
                    FIXED_TOKEN_LIFETIME_SECONDS,
                    FIXED_TOKEN_LIFETIME_SECONDS / 60,
                )
            except Exception as exc:
                _LOGGER.debug(
                    "Failed to parse server expiry '%s': %s - using fixed %d seconds",
                    expires_str,
                    exc,
                    FIXED_TOKEN_LIFETIME_SECONDS,
                )
        else:
            _LOGGER.debug(
                "No server expiry provided - using fixed %d seconds (%.1f minutes)",
                FIXED_TOKEN_LIFETIME_SECONDS,
                FIXED_TOKEN_LIFETIME_SECONDS / 60,
            )

        # Always return fixed 15-minute lifetime regardless of server response
        _LOGGER.info(
            "Applied workaround: Using fixed token lifetime of %d seconds "
            "(%.1f minutes) instead of server's broken expiry timestamps",
            FIXED_TOKEN_LIFETIME_SECONDS,
            FIXED_TOKEN_LIFETIME_SECONDS / 60,
        )

        return FIXED_TOKEN_LIFETIME_SECONDS

    async def authenticate(self) -> AuthTokens:
        """Perform complete OAuth2 authentication flow using working NextAuth flow."""
        try:
            async with get_async_client(self._hass) as client:
                _LOGGER.debug("Starting working OAuth flow...")

                # Step 1: Initialize Fortum session
                csrf_token = await self._initialize_fortum_session(client)

                # Step 2: Get OAuth URL from signin
                oauth_url = await self._initiate_oauth_signin(client, csrf_token)

                # Step 3: Perform SSO authentication
                updated_oauth_url = await self._perform_sso_authentication(
                    client, oauth_url
                )

                # Use updated OAuth URL if provided, otherwise use original
                final_oauth_url = updated_oauth_url if updated_oauth_url else oauth_url

                # Step 4: Complete OAuth authorization flow
                await self._complete_oauth_authorization(client, final_oauth_url)

                # Step 5: Verify session is established
                session_data = await self._verify_session_established(client)

                _LOGGER.info("OAuth flow completed successfully")

                # Store session cookies with domain prioritization to fix conflicts
                self._session_cookies = self._extract_prioritized_cookies(client)

                # Extract real tokens from session data
                user_data = session_data.get("user", {})
                access_token = user_data.get("accessToken", SESSION_BASED_TOKEN)
                id_token = user_data.get("idToken", SESSION_BASED_TOKEN)

                # DEBUG: Log the entire session data to understand structure
                _LOGGER.debug("Complete session data structure: %s", session_data)
                _LOGGER.debug("Complete user data structure: %s", user_data)

                expires_str = user_data.get("expires")

                # Calculate token expiry with proper timezone handling
                expires_in = self._process_token_expiry(expires_str)

                # Create tokens with real access token
                self._tokens = AuthTokens(
                    access_token=access_token,
                    refresh_token=SESSION_BASED_TOKEN,  # No refresh token in this flow
                    token_type=BEARER_TOKEN_TYPE,
                    expires_in=expires_in,
                    id_token=id_token,
                )
                self._token_expiry = time.time() + expires_in

                # Store session data for later use
                self._session_data = session_data

                # Start background token monitoring for proactive renewal
                self.start_token_monitoring()

                return self._tokens

        except Exception as exc:
            _LOGGER.exception("Authentication failed")
            raise AuthenticationError(f"Authentication failed: {exc}") from exc

    async def _initialize_fortum_session(self, client) -> str:
        """Initialize Fortum session and get CSRF token."""
        # Get providers
        providers_resp = await client.get(
            "https://www.fortum.com/se/el/api/auth/providers"
        )
        if providers_resp.status_code != 200:
            raise OAuth2Error(f"Providers fetch failed: {providers_resp.status_code}")

        # Get CSRF token
        csrf_resp = await client.get("https://www.fortum.com/se/el/api/auth/csrf")
        if csrf_resp.status_code != 200:
            raise OAuth2Error(f"CSRF fetch failed: {csrf_resp.status_code}")

        csrf_data = csrf_resp.json()
        csrf_token = csrf_data.get("csrfToken")
        if not csrf_token:
            raise OAuth2Error("No CSRF token received")

        _LOGGER.debug("Got CSRF token: %s...", csrf_token[:20])
        return csrf_token

    async def _initiate_oauth_signin(self, client, csrf_token: str) -> str:
        """Initiate OAuth signin and get OAuth URL."""
        signin_data = {
            "csrfToken": csrf_token,
            "callbackUrl": "https://www.fortum.com/se/el/inloggad/oversikt",
            "json": "true",
        }

        signin_resp = await client.post(
            "https://www.fortum.com/se/el/api/auth/signin/ciamprod",
            json=signin_data,
            headers={"Content-Type": CONTENT_TYPE_JSON},
        )

        if signin_resp.status_code != 200:
            raise OAuth2Error(f"Signin initiation failed: {signin_resp.status_code}")

        signin_result = signin_resp.json()
        oauth_url = signin_result.get("url")
        if not oauth_url:
            raise OAuth2Error("No OAuth URL received from signin")

        _LOGGER.debug("Got OAuth URL: %s...", oauth_url[:80])
        return oauth_url

    async def _perform_sso_authentication(self, client, oauth_url: str) -> str | None:
        """Perform SSO authentication with credentials.

        Returns:
            Updated OAuth URL if provided by the SSO response, otherwise None.
        """
        try:
            # Step 1: Navigate to OAuth URL to establish session
            _LOGGER.debug("Navigating to OAuth URL to establish session")
            response = await client.get(oauth_url)
            _LOGGER.debug("OAuth page status: %d", response.status_code)

            if response.status_code != 200:
                _LOGGER.warning("OAuth page returned %d", response.status_code)
                # Continue anyway, as authentication might still work

            # Step 2: Use ForgeRock JSON API for authentication
            _LOGGER.debug("Using ForgeRock JSON API for SSO authentication")

            auth_url = (
                "https://sso.fortum.com/am/json/realms/root/realms/alpha/authenticate"
            )

            auth_params = {
                "locale": "sv",
                "authIndexType": "service",
                "authIndexValue": "SeB2COGWLogin",
                "goto": oauth_url,
            }

            auth_full_url = f"{auth_url}?{urlencode(auth_params)}"

            # Initialize authentication
            _LOGGER.debug("Initializing ForgeRock authentication")
            init_resp = await client.post(
                auth_full_url,
                headers={
                    "accept-api-version": "protocol=1.0,resource=2.1",
                    "content-type": CONTENT_TYPE_JSON,
                },
                json={},
            )

            if init_resp.status_code != 200:
                raise OAuth2Error(f"Auth init failed: {init_resp.status_code}")

            init_data = init_resp.json()
            _LOGGER.debug("Auth init response: %s", init_data)

            # Check if authId is present
            auth_id = init_data.get("authId")
            if not auth_id:
                # If no authId, check for successUrl which indicates we should
                # proceed directly
                success_url = init_data.get("successUrl")
                if success_url:
                    _LOGGER.debug(
                        "No authId found, but successUrl present. "
                        "Using successUrl as OAuth URL: %s...",
                        success_url[:80],
                    )
                    return success_url  # Return the successUrl to use as OAuth URL
                else:
                    raise OAuth2Error(
                        f"No authId or successUrl in init response: {init_data}"
                    )

            callbacks = init_data.get("callbacks", [])

            # Submit credentials using callback structure
            _LOGGER.debug("Submitting credentials via ForgeRock API")
            for callback in callbacks:
                if callback.get("type") == "StringAttributeInputCallback":
                    callback["input"] = [
                        {"name": "IDToken1", "value": self._username},
                        {"name": "IDToken1validateOnly", "value": False},
                    ]
                elif callback.get("type") == "PasswordCallback":
                    callback["input"] = [{"name": "IDToken2", "value": self._password}]

            login_payload = {"authId": auth_id, "callbacks": callbacks}

            login_resp = await client.post(
                auth_full_url,
                headers={
                    "accept-api-version": "protocol=1.0,resource=2.1",
                    "content-type": CONTENT_TYPE_JSON,
                },
                json=login_payload,
            )

            if login_resp.status_code != 200:
                raise OAuth2Error(f"Login failed: {login_resp.status_code}")

            login_data = login_resp.json()
            _LOGGER.debug(
                "SSO login successful, token: %s...",
                login_data.get("tokenId", "None")[:30],
            )

            # Return None to indicate using the original OAuth URL
            return None

        except Exception as exc:
            _LOGGER.error("SSO authentication failed: %s", exc)
            raise OAuth2Error(f"SSO authentication failed: {exc}") from exc

    async def _complete_oauth_authorization(self, client, oauth_url: str) -> None:
        """Complete OAuth authorization flow."""
        try:
            oauth_completion_resp = await client.get(oauth_url)

            if oauth_completion_resp.status_code != 302:
                _LOGGER.warning(
                    "OAuth completion returned %d instead of redirect",
                    oauth_completion_resp.status_code,
                )
                return

            # Follow the callback redirect chain
            callback_url = oauth_completion_resp.headers.get("location")
            if not callback_url or AUTHORIZATION_CODE_PARAM not in callback_url:
                _LOGGER.warning("No authorization code in callback URL")
                return

            _LOGGER.debug("Following callback URL...")

            # Follow callback to complete flow
            callback_resp = await client.get(callback_url)

            # May get additional redirects
            if callback_resp.status_code == 302:
                final_redirect = callback_resp.headers.get("location")
                if final_redirect:
                    _LOGGER.debug("Following final redirect...")
                    await client.get(final_redirect)

            _LOGGER.debug("OAuth authorization flow completed")

        except Exception as exc:
            _LOGGER.error("OAuth authorization completion failed: %s", exc)
            raise OAuth2Error(f"OAuth authorization failed: {exc}") from exc

    async def _verify_session_established(self, client) -> dict[str, Any]:
        """Verify that session is properly established."""
        session_resp = await client.get("https://www.fortum.com/se/el/api/auth/session")

        if session_resp.status_code != 200:
            raise OAuth2Error(
                f"Session verification failed: {session_resp.status_code}"
            )

        session_data = session_resp.json()
        if not session_data.get("user"):
            raise OAuth2Error("No user data in session")

        _LOGGER.debug("Session verified successfully")

        # Give the server time to propagate the session for better reliability
        # Increased from 0.3s to 3.0s for better session propagation
        _LOGGER.debug("Waiting for session propagation (3.0s)")
        await asyncio.sleep(3.0)

        # Perform a non-blocking session validation check for informational purposes
        # This is purely for logging and won't fail authentication if it doesn't work
        # since the session often takes additional time to propagate across endpoints
        validation_success = await self._validate_session_against_api(client)
        if validation_success:
            _LOGGER.debug("Session validation check passed - session is ready")
        else:
            _LOGGER.info(
                "Session validation check failed during authentication, but this is "
                "normal due to session propagation delays. Session will be available "
                "for API calls shortly."
            )

        return session_data

    async def refresh_access_token(self) -> AuthTokens:
        """Refresh the access token using refresh token."""
        if not self._tokens or not self._tokens.refresh_token:
            raise AuthenticationError("No refresh token available")

        # Handle session-based authentication - can't refresh, need to re-authenticate
        if self._tokens.refresh_token == SESSION_BASED_TOKEN:
            _LOGGER.debug(
                "Session-based token detected, performing full re-authentication"
            )
            return await self.authenticate()

        try:
            _LOGGER.debug("Attempting to refresh access token")
            async with get_async_client(self._hass) as client:
                response = await client.post(
                    APIEndpoints.TOKEN_EXCHANGE,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self._tokens.refresh_token,
                        "client_id": self._client_id,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    _LOGGER.error(
                        "Token refresh failed with status %d: %s",
                        response.status_code,
                        response.text,
                    )
                    raise OAuth2Error(
                        f"Token refresh failed: {response.status_code} {response.text}"
                    )

                token_data = response.json()
                self._tokens = AuthTokens.from_api_response(token_data)
                self._token_expiry = time.time() + self._tokens.expires_in
                _LOGGER.debug("Successfully refreshed access token")

                # Restart token monitoring with new expiry time
                self.start_token_monitoring()

                return self._tokens

        except Exception as exc:
            _LOGGER.exception("Token refresh failed")
            raise AuthenticationError(f"Token refresh failed: {exc}") from exc

    def _generate_code_verifier(self, length: int = 128) -> str:
        """Generate a secure code verifier."""
        return base64.urlsafe_b64encode(os.urandom(length)).decode("utf-8").rstrip("=")

    def _generate_code_challenge(self, code_verifier: str) -> str:
        """Generate code challenge from verifier."""
        challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(challenge).decode("utf-8").rstrip("=")

    def _generate_state(self) -> str:
        """Generate random state parameter."""
        return str(uuid.uuid4())

    def _generate_acr_sig(self, code_verifier: str) -> str:
        """Generate ACR signature."""
        signature = hmac.new(
            self._secret_key.encode("utf-8"),
            msg=code_verifier.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        return base64.urlsafe_b64encode(signature.digest()).decode("utf-8").rstrip("=")

    def _construct_authorization_url(
        self, config: dict[str, Any], code_challenge: str, state: str
    ) -> str:
        """Construct OAuth2 authorization URL."""
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(OAUTH_SCOPE),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "acr_values": "seb2cogwlogin",
            "locale": "sv",
            "ui_locales": "sv",
            "acr": "seb2cogwlogin",
            "response_mode": "query",
        }
        return f"{config['authorization_endpoint']}?{urlencode(params)}"

    async def _fetch_openid_configuration(self) -> dict[str, Any]:
        """Fetch OpenID configuration."""
        async with get_async_client(self._hass) as client:
            response = await client.get(APIEndpoints.OPENID_CONFIG)
            if response.status_code != 200:
                raise OAuth2Error(
                    f"Failed to fetch OpenID config: {response.status_code}"
                )
            return response.json()

    async def _initiate_session(self, client, auth_url: str) -> None:
        """Initiate OAuth2 session."""
        response = await client.get(auth_url, follow_redirects=True)
        if response.status_code != 200:
            raise OAuth2Error(f"Session initiation failed: {response.status_code}")

    async def _authenticate_user(self, client) -> dict[str, Any]:
        """Authenticate user with credentials."""
        # Get auth ID
        response = await client.post(APIEndpoints.AUTH_INIT)
        if response.status_code != 200:
            raise OAuth2Error(f"Auth initiation failed: {response.status_code}")

        auth_data = response.json()
        auth_id = auth_data.get("authId")
        if not auth_id:
            raise OAuth2Error("No authId received")

        # Submit credentials
        login_payload = {
            "authId": auth_id,
            "callbacks": [
                {
                    "type": "StringAttributeInputCallback",
                    "output": [
                        {"name": "name", "value": "mail"},
                        {"name": "prompt", "value": "Email Address"},
                        {"name": "required", "value": True},
                        {"name": "policies", "value": {}},
                        {"name": "failedPolicies", "value": []},
                        {"name": "validateOnly", "value": False},
                        {"name": "value", "value": ""},
                    ],
                    "input": [
                        {"name": "IDToken1", "value": self._username},
                        {"name": "IDToken1validateOnly", "value": False},
                    ],
                    "_id": 0,
                },
                {
                    "type": "PasswordCallback",
                    "output": [{"name": "prompt", "value": "Password"}],
                    "input": [{"name": "IDToken2", "value": self._password}],
                    "_id": 1,
                },
            ],
        }

        response = await client.post(APIEndpoints.AUTH_INIT, json=login_payload)
        if response.status_code != 200:
            raise OAuth2Error(f"User authentication failed: {response.status_code}")

        return response.json()

    async def _get_user_session(self, client) -> dict[str, Any]:
        """Get user session information."""
        response = await client.post(
            APIEndpoints.USER_SESSION,
            headers={"accept-api-version": "protocol=1.0,resource=2.0"},
            json={},
        )
        if response.status_code != 200:
            raise OAuth2Error(f"Session retrieval failed: {response.status_code}")
        return response.json()

    async def _fetch_user_details(self, client, user_id: str) -> dict[str, Any]:
        """Fetch user details."""
        url = APIEndpoints.get_user_details_url(user_id)
        response = await client.get(url)
        if response.status_code != 200:
            raise OAuth2Error(f"User details fetch failed: {response.status_code}")
        return response.json()

    async def _validate_goto(
        self, client, code_challenge: str, state: str
    ) -> dict[str, Any]:
        """Validate goto URL."""
        goto_url = (
            f"https://sso.fortum.com:443/am/oauth2/authorize?"
            f"client_id={self._client_id}&redirect_uri={self._redirect_uri}&"
            f"response_type=code&scope={'%20'.join(OAUTH_SCOPE)}&"
            f"state={state}&code_challenge={code_challenge}&"
            f"code_challenge_method=S256&response_mode=query&"
            f"acr_values=seb2cogwlogin&acr=seb2cogwlogin&"
            f"locale=sv&ui_locales=sv"
        )

        response = await client.post(
            APIEndpoints.VALIDATE_GOTO,
            headers={"accept-api-version": "protocol=2.1,resource=3.0"},
            json={"goto": goto_url},
        )

        if response.status_code != 200:
            raise OAuth2Error(f"Goto validation failed: {response.status_code}")
        return response.json()

    async def _follow_success_url(self, client, success_url: str, acr_sig: str) -> str:
        """Follow success URL to get authorization code."""
        response = await client.get(
            f"{success_url}&acr_sig={acr_sig}", follow_redirects=True
        )

        # Look for authorization code in redirect chain
        for redirect_response in response.history:
            location = redirect_response.headers.get("Location", "")
            if AUTHORIZATION_CODE_PARAM in location:
                parsed_url = urlparse(location)
                code = parse_qs(parsed_url.query).get("code", [None])[0]
                if code:
                    return code

        # Check final URL
        if AUTHORIZATION_CODE_PARAM in str(response.url):
            parsed_url = urlparse(str(response.url))
            code = parse_qs(parsed_url.query).get("code", [None])[0]
            if code:
                return code

        raise OAuth2Error("No authorization code found in response")

    async def _exchange_code_for_tokens(
        self, client, auth_code: str, code_verifier: str
    ) -> AuthTokens:
        """Exchange authorization code for access tokens."""
        response = await client.post(
            APIEndpoints.TOKEN_EXCHANGE,
            data={
                "grant_type": "authorization_code",
                "redirect_uri": self._redirect_uri,
                "code": auth_code,
                "code_verifier": code_verifier,
                "client_id": self._client_id,
            },
        )

        if response.status_code != 200:
            raise OAuth2Error(
                f"Token exchange failed: {response.status_code} {response.text}"
            )

        return AuthTokens.from_api_response(response.json())

    async def _validate_session_against_api(self, client) -> bool:
        """Validate that the session works against actual API endpoints."""
        try:
            # Test against the session endpoint that the client actually uses
            test_url = "https://www.fortum.com/se/el/api/auth/session"
            response = await client.get(test_url)

            if response.status_code == 200:
                _LOGGER.debug("Session validation against API successful")
                return True
            elif response.status_code == 401:
                _LOGGER.warning(
                    "Session validation failed with 401 - session not ready"
                )
                return False
            else:
                _LOGGER.warning(
                    "Session validation returned status %d", response.status_code
                )
                return False
        except Exception as exc:
            _LOGGER.warning("Session validation failed with exception: %s", exc)
            return False

    def _extract_prioritized_cookies(self, client) -> dict[str, str]:
        """Extract cookies with domain prioritization to prevent stale cookie usage.

        Domain-specific cookies are prioritized over empty domain cookies to ensure
        fresh session tokens are used instead of stale ones.
        """
        domain_cookies = {}
        empty_domain_cookies = {}

        for cookie in client.cookies.jar:
            if cookie.value is None:
                continue

            cookie_preview = (
                cookie.value[:20] + "..." if len(cookie.value) > 20 else cookie.value
            )
            domain = getattr(cookie, "domain", "")
            path = getattr(cookie, "path", "None")

            if domain:
                # Domain-specific cookie (prioritized)
                domain_cookies[cookie.name] = cookie.value
                _LOGGER.debug(
                    "Captured domain cookie: %s=%s (domain=%s, path=%s)",
                    cookie.name,
                    cookie_preview,
                    domain,
                    path,
                )
            elif cookie.name not in domain_cookies:
                # Empty domain cookie only if no domain version exists
                empty_domain_cookies[cookie.name] = cookie.value
                _LOGGER.debug(
                    "Captured empty-domain cookie: %s=%s (domain=%s, path=%s)",
                    cookie.name,
                    cookie_preview,
                    domain or "None",
                    path,
                )
            else:
                _LOGGER.debug(
                    "Skipped empty-domain cookie %s - domain version exists",
                    cookie.name,
                )

        # Combine with domain cookies taking priority
        result_cookies = {}
        result_cookies.update(empty_domain_cookies)
        result_cookies.update(domain_cookies)  # Domain cookies override empty ones

        _LOGGER.debug("Stored %d session cookies for API calls", len(result_cookies))
        return result_cookies

    def _parse_server_datetime(self, expires_str: str) -> datetime:
        """Parse server datetime with robust timezone handling.

        Args:
            expires_str: Datetime string from server

        Returns:
            Parsed datetime object in UTC

        Raises:
            ValueError: If datetime string cannot be parsed
        """
        try:
            # Handle common server datetime formats
            if expires_str.endswith("Z"):
                # ISO format with Z (UTC)
                return datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            elif "+00:00" in expires_str:
                # ISO format with explicit UTC timezone
                return datetime.fromisoformat(expires_str)
            elif "+" in expires_str or expires_str.count("-") > 2:
                # ISO format with timezone offset
                return datetime.fromisoformat(expires_str)
            else:
                # Assume UTC if no timezone info
                dt = datetime.fromisoformat(expires_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return dt
        except ValueError as exc:
            raise ValueError(
                f"Cannot parse datetime string '{expires_str}': {exc}"
            ) from exc

    def start_token_monitoring(self) -> None:
        """Start background token monitoring for proactive renewal."""
        if self._monitoring_enabled and self._token_monitor_task:
            return  # Already running

        self._monitoring_enabled = True
        self._token_monitor_task = asyncio.create_task(self._monitor_token_expiry())
        _LOGGER.debug("Started background token monitoring")

    async def stop_token_monitoring(self) -> None:
        """Stop background token monitoring."""
        self._monitoring_enabled = False
        if self._token_monitor_task and not self._token_monitor_task.done():
            self._token_monitor_task.cancel()
            try:
                await self._token_monitor_task
            except asyncio.CancelledError:
                pass
        self._token_monitor_task = None
        _LOGGER.debug("Stopped background token monitoring")

    def _should_renew_token(self) -> tuple[bool, bool]:
        """Check if token should be renewed and if it's urgent.

        Returns:
            Tuple of (should_renew, is_urgent)
        """
        if not self._tokens or not self._token_expiry:
            return False, False

        time_until_expiry = self.time_until_expiry()

        # Check if renewal is needed (within 5 minutes for 15-minute tokens)
        if time_until_expiry <= 300:  # 5 minutes
            is_urgent = time_until_expiry <= URGENT_RENEWAL_THRESHOLD_SECONDS
            return True, is_urgent

        return False, False

    async def _perform_proactive_renewal(self, is_urgent: bool) -> bool:
        """Perform proactive token renewal.

        Args:
            is_urgent: Whether this is an urgent renewal

        Returns:
            True if renewal was successful, False otherwise
        """
        time_until_expiry = self.time_until_expiry()

        if is_urgent:
            _LOGGER.info(
                "Token expires in %.1f minutes, performing immediate renewal",
                time_until_expiry / 60,
            )
        else:
            _LOGGER.debug(
                "Token expires in %.1f minutes, will monitor for renewal",
                time_until_expiry / 60,
            )
            return True  # No action needed yet

        try:
            await self.refresh_access_token()
            _LOGGER.info("Proactive token renewal successful")
            return True
        except Exception as exc:
            _LOGGER.error("Proactive token renewal failed: %s", exc)
            return False

    def _calculate_check_interval(self) -> int:
        """Calculate the next check interval in seconds."""
        if not self._tokens or not self._token_expiry:
            return 120  # 2 minutes if no token

        time_until_expiry = self.time_until_expiry()
        # For 15-minute tokens, check more frequently (min 15s, max 60s)
        # Check when renewal is needed (5 minutes before expiry)
        return min(60, max(15, int(time_until_expiry - 300)))

    async def _monitor_token_expiry(self) -> None:
        """Background task to monitor token expiry and proactively renew tokens."""
        _LOGGER.debug("Token monitoring task started")

        while self._monitoring_enabled:
            try:
                should_renew, is_urgent = self._should_renew_token()

                if should_renew:
                    success = await self._perform_proactive_renewal(is_urgent)
                    if not success and is_urgent:
                        # Wait before retrying if urgent renewal failed
                        await asyncio.sleep(30)
                        continue

                # Calculate next check interval and sleep
                check_interval = self._calculate_check_interval()
                await asyncio.sleep(check_interval)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                _LOGGER.exception("Error in token monitoring task: %s", exc)
                await asyncio.sleep(60)  # Wait before retrying

        _LOGGER.debug("Token monitoring task stopped")
