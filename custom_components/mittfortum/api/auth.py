"""OAuth2 authentication client for MittFortum."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlencode, urlparse
import uuid

from homeassistant.helpers.httpx_client import get_async_client

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from ..const import OAUTH_CLIENT_ID, OAUTH_REDIRECT_URI, OAUTH_SCOPE, OAUTH_SECRET_KEY
from ..exceptions import AuthenticationError, OAuth2Error
from ..models import AuthTokens
from .endpoints import APIEndpoints

_LOGGER = logging.getLogger(__name__)


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

    def is_token_expired(self) -> bool:
        """Check if the current token is expired."""
        if not self._token_expiry:
            return True
        return time.time() >= self._token_expiry

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
                await self._perform_sso_authentication(client, oauth_url)

                # Step 4: Complete OAuth authorization flow
                await self._complete_oauth_authorization(client, oauth_url)

                # Step 5: Verify session is established
                session_data = await self._verify_session_established(client)

                _LOGGER.info("OAuth flow completed successfully")

                # Store session cookies for later API calls
                self._session_cookies = {}
                for cookie in client.cookies.jar:
                    if cookie.value is not None:
                        self._session_cookies[cookie.name] = cookie.value

                _LOGGER.debug(
                    "Stored %d session cookies for API calls",
                    len(self._session_cookies),
                )

                # Extract real tokens from session data
                user_data = session_data.get("user", {})
                access_token = user_data.get("accessToken", "session_based")
                id_token = user_data.get("idToken", "session_based")
                expires_str = user_data.get("expires")

                # Calculate token expiry
                expires_in = 3600  # Default to 1 hour
                if expires_str:
                    try:
                        from datetime import datetime

                        expires_dt = datetime.fromisoformat(
                            expires_str.replace("Z", "+00:00")
                        )
                        expires_in = int((expires_dt - datetime.now()).total_seconds())
                        if expires_in < 0:
                            expires_in = 3600  # Default if expired
                    except Exception:
                        expires_in = 3600

                # Create tokens with real access token
                self._tokens = AuthTokens(
                    access_token=access_token,
                    refresh_token="session_based",  # No refresh token in this flow
                    token_type="Bearer",
                    expires_in=expires_in,
                    id_token=id_token,
                )
                self._token_expiry = time.time() + expires_in

                # Store session data for later use
                self._session_data = session_data

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
            "callbackUrl": "https://www.fortum.com/se/el/sv/private/overview",
            "json": "true",
        }

        signin_resp = await client.post(
            "https://www.fortum.com/se/el/api/auth/signin/ciamprod?ui_locales=sv",
            data=signin_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if signin_resp.status_code != 200:
            raise OAuth2Error(f"Signin initiation failed: {signin_resp.status_code}")

        signin_result = signin_resp.json()
        oauth_url = signin_result.get("url")
        if not oauth_url:
            raise OAuth2Error("No OAuth URL received from signin")

        _LOGGER.debug("Got OAuth URL: %s...", oauth_url[:80])
        return oauth_url

    async def _perform_sso_authentication(self, client, oauth_url: str) -> None:
        """Perform SSO authentication with credentials."""
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
        init_resp = await client.post(
            auth_full_url,
            headers={
                "accept-api-version": "protocol=1.0,resource=2.1",
                "content-type": "application/json",
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
            raise OAuth2Error(f"No authId in init response: {init_data}")

        callbacks = init_data.get("callbacks", [])

        # Submit credentials
        for callback in callbacks:
            if callback.get("type") == "StringAttributeInputCallback":
                callback["input"] = [
                    {"name": "IDToken5", "value": self._username},
                    {"name": "IDToken5validateOnly", "value": False},
                ]
            elif callback.get("type") == "PasswordCallback":
                callback["input"] = [{"name": "IDToken6", "value": self._password}]

        login_payload = {"authId": auth_id, "callbacks": callbacks}

        login_resp = await client.post(
            auth_full_url,
            headers={
                "accept-api-version": "protocol=1.0,resource=2.1",
                "content-type": "application/json",
            },
            json=login_payload,
        )

        if login_resp.status_code != 200:
            raise OAuth2Error(f"Login failed: {login_resp.status_code}")

        login_data = login_resp.json()
        _LOGGER.debug(
            "SSO login successful, token: %s...", login_data.get("tokenId", "None")[:30]
        )

    async def _complete_oauth_authorization(self, client, oauth_url: str) -> None:
        """Complete OAuth authorization flow."""
        oauth_completion_resp = await client.get(oauth_url)

        if oauth_completion_resp.status_code != 302:
            raise OAuth2Error(
                f"OAuth completion failed: {oauth_completion_resp.status_code}"
            )

        # Follow the callback redirect chain
        callback_url = oauth_completion_resp.headers.get("location")
        if not callback_url or "code=" not in callback_url:
            raise OAuth2Error("No authorization code in callback URL")

        _LOGGER.debug("Following callback URL...")

        # Follow callback to complete flow
        callback_resp = await client.get(callback_url)

        # May get additional redirects
        if callback_resp.status_code == 302:
            final_redirect = callback_resp.headers.get("location")
            if final_redirect:
                await client.get(final_redirect)

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
        return session_data

    async def refresh_access_token(self) -> AuthTokens:
        """Refresh the access token using refresh token."""
        if not self._tokens or not self._tokens.refresh_token:
            raise AuthenticationError("No refresh token available")

        try:
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
                    raise OAuth2Error(
                        f"Token refresh failed: {response.status_code} {response.text}"
                    )

                token_data = response.json()
                self._tokens = AuthTokens.from_api_response(token_data)
                self._token_expiry = time.time() + self._tokens.expires_in

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
            if "code=" in location:
                parsed_url = urlparse(location)
                code = parse_qs(parsed_url.query).get("code", [None])[0]
                if code:
                    return code

        # Check final URL
        if "code=" in str(response.url):
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
