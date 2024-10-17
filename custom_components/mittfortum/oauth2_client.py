import base64
import hashlib
import hmac
import logging
import os
import time
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
import uuid

from homeassistant.helpers.httpx_client import get_async_client

_LOGGER = logging.getLogger(__name__)


class OAuth2ClientError(Exception):
    """Custom exception for OAuth2Client errors."""


class OAuth2Client:
    """Encapsulates OAuth2 authentication logic for Fortum's API."""

    def __init__(
        self,
        client_id="swedenmypagesprod",
        redirect_uri="https://www.mittfortum.se",
        secret_key="shared_secret",
        username=None,
        password=None,
        HomeAssistant=None,
    ):
        """Initialize the OAuth2Client."""
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.secret_key = secret_key
        self.username = username
        self.password = password
        self.session_token = None
        self.refresh_token = None
        self.id_token = None
        self.token_expiry = None
        self.session = None
        self.hass = HomeAssistant

    async def __aenter__(self):
        self.session = get_async_client(self.hass)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def generate_code_verifier(self, length: int = 128) -> str:
        """Generate a secure code verifier."""
        return base64.urlsafe_b64encode(os.urandom(length)).decode("utf-8").rstrip("=")

    async def generate_code_challenge(self, code_verifier: str) -> str:
        """Generate a code challenge based on the verifier."""
        code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(code_challenge).decode("utf-8").rstrip("=")

    async def generate_state(self) -> str:
        """Generate a random state parameter for the auth request."""
        return str(uuid.uuid4())

    async def construct_authorization_url(
        self, config: dict[str, Any], code_challenge: str, state: str
    ) -> str:
        """Construct the OAuth2 authorization URL."""
        authorization_endpoint = config.get("authorization_endpoint")
        scope = ["openid", "profile", "crmdata"]
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scope),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "acr_values": "seb2clogin",
            "response_mode": "query",
        }
        return f"{authorization_endpoint}?{urlencode(params)}"

    async def fetch_openid_configuration(self) -> dict[str, Any]:
        """Fetch OpenID configuration from the provider."""
        openid_config_url = "https://sso.fortum.com/.well-known/openid-configuration"
        response = await self.session.get(openid_config_url)

        if response.status_code == 200:
            return response.json()
        raise OAuth2ClientError(
            f"Failed to fetch OpenID configuration: {response.status_code}"
        )

    async def exchange_code_for_access_token(
        self, code: str, code_verifier: str
    ) -> dict[str, Any]:
        """Exchange authorization code for access token."""
        url = "https://sso.fortum.com/am/oauth2/access_token"
        payload = {
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
            "code": code,
            "code_verifier": code_verifier,
            "client_id": self.client_id,
        }

        response = await self.session.post(url, data=payload)
        if response.status_code != 200:
            raise OAuth2ClientError(
                f"Failed to exchange code for access token: {response.status_code} {response.text}"
            )
        tokens = response.json()
        self.session_token = tokens.get("access_token")
        self.refresh_token = tokens.get("refresh_token")
        return tokens

    async def authenticate_user(self) -> dict[str, Any]:
        """Authenticate the user and return the login response."""
        initial_auth_url = "https://sso.fortum.com/am/json/realms/root/realms/alpha/authenticate?authIndexType=service&authIndexValue=SeB2CLogin"

        response = await self.session.post(initial_auth_url)

        if response.status_code == 200:
            response_data = response.json()
            auth_id = response_data.get("authId")
        else:
            raise OAuth2ClientError(
                f"Failed to initiate authentication: {response.status_code} {response.text}"
            )

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
                        {"name": "IDToken1", "value": self.username},
                        {"name": "IDToken1validateOnly", "value": False},
                    ],
                    "_id": 0,
                },
                {
                    "type": "PasswordCallback",
                    "output": [{"name": "prompt", "value": "Password"}],
                    "input": [{"name": "IDToken2", "value": self.password}],
                    "_id": 1,
                },
            ],
        }

        login_response = await self.session.post(initial_auth_url, json=login_payload)

        if login_response.status_code == 200:
            return login_response.json()
        raise OAuth2ClientError(
            f"Login failed: {login_response.status_code} {login_response.text}"
        )

    async def perform_authenticated_action(self) -> dict[str, Any]:
        """Perform an authenticated action."""
        headers = {"accept-api-version": "protocol=1.0,resource=2.0"}
        response = await self.session.post(
            "https://sso.fortum.com/am/json/users?_action=idFromSession",
            headers=headers,
            json={},
        )
        if response.status_code != 200:
            raise OAuth2ClientError(f"Failed: {response.status_code} {response.text}")
        return response.json()

    async def fetch_user_details(self, user_id: str) -> dict[str, Any]:
        """Fetch details of an authenticated user."""
        user_details_url = (
            f"https://sso.fortum.com/am/json/realms/root/realms/alpha/users/{user_id}"
        )

        response = await self.session.get(user_details_url)

        if response.status_code == 200:
            return response.json()
        raise OAuth2ClientError(
            f"Failed to fetch user details: {response.status_code} {response.text}"
        )

    async def validate_goto(self, code_challenge: str, state: str) -> dict[str, Any]:
        """Validate the 'goto' URL required during the authentication flow."""
        url = "https://sso.fortum.com/am/json/realms/root/realms/alpha/users?_action=validateGoto"
        scope = ["openid", "profile", "crmdata"]
        payload = {
            "goto": (
                f"https://sso.fortum.com:443/am/oauth2/authorize?"
                f"client_id={self.client_id}&redirect_uri={self.redirect_uri}&"
                f"response_type=code&scope={'%20'.join(scope)}&"
                f"state={state}&"
                f"code_challenge={code_challenge}&"
                f"code_challenge_method=S256&response_mode=query&"
                f"acr_values=seb2clogin&acr=seb2clogin"
            )
        }

        headers = {
            "accept-api-version": "protocol=2.1,resource=3.0",
        }

        response = await self.session.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            return response.json()
        raise OAuth2ClientError(
            f"Failed to validate goto URL: {response.status_code} {response.text}"
        )

    async def generate_acr_sig(self, code_verifier: str) -> str:
        """Generate an ACR signature."""
        hmac_obj = hmac.new(
            self.secret_key.encode("utf-8"),
            msg=code_verifier.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        return base64.urlsafe_b64encode(hmac_obj.digest()).decode("utf-8").rstrip("=")

    async def follow_success_url(self, success_url: str, acr_sig: str) -> str:
        """Follow the success URL from the authentication flow."""
        response = await self.session.get(
            f"{success_url}&acr_sig={acr_sig}", follow_redirects=True
        )
        if response.status_code == 200:
            location = None
            for r in response.history:
                location = r.headers.get("Location")
            return location
        raise OAuth2ClientError(
            f"Failed to follow success URL: {response.status_code} {response.text}"
        )

    async def initiate_session(self, auth_url: str) -> None:
        """Initiate the session by navigating to the authorization URL."""
        response = await self.session.get(auth_url, follow_redirects=True)
        if response.status_code != 200:
            raise OAuth2ClientError(
                f"Failed to initiate session: {response.status_code} {response.text}"
            )

    def is_token_expired(self):
        """Check if the session token is expired."""
        return self.token_expiry is None or time.time() > self.token_expiry

    async def refresh_access_token(self) -> dict[str, Any]:
        """Refresh the access token using the refresh token."""
        url = "https://sso.fortum.com/am/oauth2/access_token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
        }

        response = await self.session.post(url, data=payload, headers=headers)
        if response.status_code != 200:
            raise OAuth2ClientError(
                f"Failed to refresh access token: {response.status_code} {response.text}"
            )
        tokens = response.json()
        self.session_token = tokens.get("access_token")
        self.refresh_token = tokens.get("refresh_token")
        self.token_expiry = time.time() + tokens["expires_in"]
        return tokens

    async def login(self) -> dict[str, Any]:
        """Perform the OAuth2 login flow."""
        async with self:
            config = await self.fetch_openid_configuration()
            code_verifier = await self.generate_code_verifier()
            code_challenge = await self.generate_code_challenge(code_verifier)
            state = await self.generate_state()

            auth_url = await self.construct_authorization_url(
                config, code_challenge, state
            )
            await self.initiate_session(auth_url)

            await self.authenticate_user()

            user_id = await self.perform_authenticated_action()
            await self.fetch_user_details(user_id["id"])

            goto_url = await self.validate_goto(code_challenge, state)

            success_url = goto_url.get("successURL")
            if success_url:
                acr_sig = await self.generate_acr_sig(code_verifier)
                final_url = await self.follow_success_url(success_url, acr_sig)

                parsed_url = urlparse(final_url)

                code = parse_qs(parsed_url.query).get("code", [None])[0]

                if code:
                    tokens = await self.exchange_code_for_access_token(
                        code, code_verifier
                    )
                    self.session_token = tokens.get("access_token")
                    self.refresh_token = tokens.get("refresh_token")
                    self.id_token = tokens.get("id_token")
                    self.token_expiry = time.time() + tokens["expires_in"]
                    return tokens
                raise OAuth2ClientError("No authorization code found in final URL.")
            raise OAuth2ClientError("No successURL found in validation response.")
