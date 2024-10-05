# oauth2_client.py

import httpx
import os
import base64
import hashlib
import hmac
import uuid
from urllib.parse import urlencode

class OAuth2Client:
    """Encapsulates OAuth2 authentication logic for Fortum's API."""

    def __init__(self, client_id, redirect_uri, secret_key="shared_secret"):
        """Initialize the OAuth2Client."""
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.secret_key = secret_key
        self.session = httpx.Client(follow_redirects=True)
        
    def fetch_openid_configuration(self):
        """Fetch OpenID configuration from the provider."""
        openid_config_url = "https://sso.fortum.com/.well-known/openid-configuration"
        response = self.session.get(openid_config_url)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch OpenID configuration: {response.status_code}")

    def generate_code_verifier(self, length=128):
        """Generate a secure code verifier."""
        if not 43 <= length <= 128:
            raise ValueError("Length must be between 43 and 128 characters.")
        random_bytes = os.urandom(length)
        code_verifier = base64.urlsafe_b64encode(random_bytes).decode("utf-8").rstrip("=")
        return code_verifier[:length]

    def generate_code_challenge(self, code_verifier):
        """Generate a code challenge based on the verifier."""
        verifier_bytes = code_verifier.encode("utf-8")
        sha256_hash = hashlib.sha256(verifier_bytes).digest()
        return base64.urlsafe_b64encode(sha256_hash).decode("utf-8").rstrip("=")

    def generate_state(self):
        """Generate a random state parameter for the auth request."""
        return str(uuid.uuid4())

    def construct_authorization_url(self, config, code_challenge, state):
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

    def initiate_session(self, auth_url):
        """Initiate an OAuth session."""
        response = self.session.get(auth_url)
        if response.status_code != 200:
            raise Exception(f"Failed to access authorization URL: {response.status_code}")

    def authenticate_user(self, username, password):
        """Authenticate the user and return the login response."""
        initial_auth_url = "https://sso.fortum.com/am/json/realms/root/realms/alpha/authenticate?authIndexType=service&authIndexValue=SeB2CLogin"

        response = self.session.post(initial_auth_url)
        if response.status_code != 200:
            raise Exception(f"Failed to initiate authentication: {response.status_code}")

        response_data = response.json()
        auth_id = response_data.get("authId")

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
                        {"name": "IDToken1", "value": username},
                        {"name": "IDToken1validateOnly", "value": False},
                    ],
                    "_id": 0,
                },
                {
                    "type": "PasswordCallback",
                    "output": [{"name": "prompt", "value": "Password"}],
                    "input": [{"name": "IDToken2", "value": password}],
                    "_id": 1,
                },
            ],
        }

        login_response = self.session.post(initial_auth_url, json=login_payload)
        if login_response.status_code != 200:
            raise Exception(f"Login failed: {login_response.status_code} {login_response.text}")

        return login_response

    def perform_authenticated_action(self):
        """Perform an authenticated action."""
        headers = {"accept-api-version": "protocol=1.0,resource=2.0"}
        response = self.session.post("https://sso.fortum.com/am/json/users?_action=idFromSession", headers=headers, json={})
        if response.status_code != 200:
            raise Exception(f"Failed: {response.status_code} {response.text}")
        return response.json()

    def follow_success_url(self, success_url, acr_sig):
        """Follow the success URL from the authentication flow."""
        if "?" in success_url:
            success_url += f"&acr_sig={acr_sig}"
        else:
            success_url += f"?acr_sig={acr_sig}"

        response = self.session.get(success_url)
        if response.status_code != 200:
            raise Exception(f"Failed to follow successURL: {response.status_code} {response.text}")

        # Extract and return the redirect location
        for r in response.history:
            location = r.headers.get("Location")
            if location: return location

    def exchange_code_for_access_token(self, code, code_verifier):
        """Exchange authorization code for access token."""
        url = "https://sso.fortum.com/am/oauth2/access_token"
        payload = {
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
            "code": code,
            "code_verifier": code_verifier,
            "client_id": self.client_id,
        }

        response = self.session.post(url, data=payload)
        if response.status_code != 200:
            raise Exception(f"Failed to exchange code for access token: {response.status_code} {response.text}")
        return response.json()

    def generate_acr_sig(self, code_verifier):
        """Generate an ACR signature."""
        hmac_obj = hmac.new(self.secret_key.encode("utf-8"), msg=code_verifier.encode("utf-8"), digestmod=hashlib.sha256)
        return base64.urlsafe_b64encode(hmac_obj.digest()).decode("utf-8").rstrip("=")

    def validate_goto(self, code_challenge, state):
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

        response = self.session.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to validate goto URL: {response.status_code} {response.text}")

    def fetch_user_details(self, user_id):
        """Fetch details of an authenticated user."""
        user_details_url = (
            f"https://sso.fortum.com/am/json/realms/root/realms/alpha/users/{user_id}"
        )

        response = self.session.get(user_details_url)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch user details: {response.status_code} {response.text}")